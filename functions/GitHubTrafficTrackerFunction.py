import json
import logging
from datetime import datetime

import boto3
import requests

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
cloudwatch = boto3.client("cloudwatch")
ssm = boto3.client("ssm")
secrets_manager = boto3.client("secretsmanager")
logs_client = boto3.client("logs")


def get_repositories():
    """Fetch repositories list from SSM Parameter Store"""
    try:
        response = ssm.get_parameter(Name="GitHubTrafficRepos")
        repos = response["Parameter"]["Value"].split(";")
        return [repo.strip() for repo in repos if repo.strip()]
    except Exception as e:
        logger.error(f"Error fetching repositories from SSM: {str(e)}")
        raise


def get_access_tokens():
    """Fetch access tokens from Secrets Manager"""
    try:
        response = secrets_manager.get_secret_value(
            SecretId="GitHubTrafficAccessTokens"
        )
        return json.loads(response["SecretString"])
    except Exception as e:
        logger.error(f"Error fetching access tokens from Secrets Manager: {str(e)}")
        raise


def get_token_for_repo(tokens, repo):
    """Get the appropriate access token for a repository"""
    for repo_config in tokens.get("repositories", []):
        if repo_config["repository"] == repo:
            return repo_config["accesstoken"]
    return tokens.get("defaulttoken")


def ensure_log_group_exists(log_group_name):
    """Ensure CloudWatch Logs group exists"""
    try:
        logs_client.create_log_group(logGroupName=log_group_name)
    except logs_client.exceptions.ResourceAlreadyExistsException:
        pass


def ensure_log_stream_exists(log_group_name, log_stream_name):
    """Ensure CloudWatch Logs stream exists"""
    try:
        logs_client.create_log_stream(
            logGroupName=log_group_name, logStreamName=log_stream_name
        )
    except logs_client.exceptions.ResourceAlreadyExistsException:
        pass


def publish_to_cloudwatch_logs(log_group_name, log_stream_name, message):
    """Publish logs to CloudWatch Logs"""
    ensure_log_group_exists(log_group_name)
    ensure_log_stream_exists(log_group_name, log_stream_name)

    try:
        logs_client.put_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            logEvents=[
                {
                    "timestamp": int(datetime.utcnow().timestamp() * 1000),
                    "message": json.dumps(message),
                }
            ],
        )
    except Exception as e:
        logger.error(f"Error publishing to CloudWatch Logs: {str(e)}")


def fetch_github_traffic_data(owner_repo, access_token, data_type):
    """
    Fetch traffic data from GitHub API
    data_type should be either 'clones' or 'views'
    """
    base_url = f"https://api.github.com/repos/{owner_repo}/traffic/{data_type}"
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        response = requests.get(base_url, headers=headers, params={"per": "day"})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {data_type} data for {owner_repo}: {str(e)}")
        raise


def publish_metrics(owner_repo, data_type, traffic_data):
    """
    Publish metrics to CloudWatch
    data_type should be either 'clones' or 'views'
    """
    # Get the data array based on data_type
    data_array = traffic_data.get(data_type, [])
    if not data_array:
        logger.warning(f"No {data_type} data found for {owner_repo}")
        return

    # Find the most recent date in the data
    latest_entry = max(data_array, key=lambda x: x["timestamp"])

    # Prepare metrics for both count and uniques
    metrics = [
        {
            "MetricName": data_type,
            "Dimensions": [
                {"Name": "type", "Value": "count"},
                {"Name": "repository", "Value": owner_repo},
            ],
            "Value": latest_entry["count"],
            "Timestamp": datetime.strptime(
                latest_entry["timestamp"], "%Y-%m-%dT%H:%M:%SZ"
            ),
            "Unit": "Count",
        },
        {
            "MetricName": data_type,
            "Dimensions": [
                {"Name": "type", "Value": "uniques"},
                {"Name": "repository", "Value": owner_repo},
            ],
            "Value": latest_entry["uniques"],
            "Timestamp": datetime.strptime(
                latest_entry["timestamp"], "%Y-%m-%dT%H:%M:%SZ"
            ),
            "Unit": "Count",
        },
    ]

    try:
        cloudwatch.put_metric_data(Namespace="GitHubTrafficTracker", MetricData=metrics)
        logger.info(f"Successfully published {data_type} metrics for {owner_repo}")
    except Exception as e:
        logger.error(f"Error publishing metrics for {owner_repo}: {str(e)}")
        raise


def process_repository(owner_repo, access_token):
    """Process a single repository's traffic data"""
    try:
        # Fetch and process clones data
        clones_data = fetch_github_traffic_data(owner_repo, access_token, "clones")
        publish_to_cloudwatch_logs(
            "github-traffic-tracker", f"{owner_repo}/clones", clones_data
        )
        publish_metrics(owner_repo, "clones", clones_data)

        # Fetch and process views data
        views_data = fetch_github_traffic_data(owner_repo, access_token, "views")
        publish_to_cloudwatch_logs(
            "github-traffic-tracker", f"{owner_repo}/views", views_data
        )
        publish_metrics(owner_repo, "views", views_data)

        return True
    except Exception as e:
        logger.error(f"Error processing repository {owner_repo}: {str(e)}")
        return False


def validate_repository_format(repo):
    """Validate repository format (owner/repo)"""
    if not repo or "/" not in repo:
        return False
    parts = repo.split("/")
    return len(parts) == 2 and all(parts)


def handle_repository_errors(repos_results):
    """Handle repository processing results and generate summary"""
    successful = [repo for repo, success in repos_results if success]
    failed = [repo for repo, success in repos_results if not success]

    summary = {
        "total_repositories": len(repos_results),
        "successful_repositories": len(successful),
        "failed_repositories": len(failed),
    }

    if failed:
        summary["failed_repos"] = failed

    return summary


def lambda_handler(event, context):
    """Main Lambda handler function"""
    try:
        # Get repositories list from SSM
        repositories = get_repositories()
        if not repositories:
            error_msg = "No repositories found in SSM Parameter Store"
            logger.error(error_msg)
            return {"statusCode": 400, "body": json.dumps({"error": error_msg})}

        # Validate repository formats
        invalid_repos = [
            repo for repo in repositories if not validate_repository_format(repo)
        ]
        if invalid_repos:
            error_msg = f"Invalid repository format found: {invalid_repos}"
            logger.error(error_msg)
            return {"statusCode": 400, "body": json.dumps({"error": error_msg})}

        # Get access tokens from Secrets Manager
        tokens = get_access_tokens()
        if not tokens or "defaulttoken" not in tokens:
            error_msg = "No default access token found in Secrets Manager"
            logger.error(error_msg)
            return {"statusCode": 400, "body": json.dumps({"error": error_msg})}

        # Process each repository
        repos_results = []
        for repo in repositories:
            token = get_token_for_repo(tokens, repo)
            success = process_repository(repo, token)
            repos_results.append((repo, success))

        # Generate execution summary
        summary = handle_repository_errors(repos_results)

        # Log summary
        logger.info(f"Execution summary: {json.dumps(summary)}")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "GitHub traffic data processing completed",
                    "summary": summary,
                }
            ),
        }

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return {"statusCode": 500, "body": json.dumps({"error": error_msg})}
