# Repo Traffic Tracker

This solution deploys a serverless application that tracks traffic statistics for GitHub repositories using AWS Lambda. It collects daily clone and view statistics for specified repositories and publishes them to Amazon CloudWatch metrics and logs.

## Features

- Tracks multiple GitHub repositories
- Collects daily clone and view statistics
- Publishes metrics to CloudWatch
- Supports repository-specific GitHub access tokens
- Runs automatically once per day
- Retains historical data in CloudWatch logs

## Prerequisites

1. An AWS account with permissions to create:
   - Lambda functions
   - IAM roles
   - CloudWatch log groups
   - EventBridge rules
   - Systems Manager parameters

2. A GitHub personal access token with the following permissions:
   - `repo` scope for private repositories
   - `public_repo` scope for public repositories

3. AWS CLI installed and configured (if deploying via CLI)

## Setup Instructions

### 1. Create GitHub Access Token Secret

Before deploying the CloudFormation template, you need to create a secret in AWS Secrets Manager:

1. Go to AWS Secrets Manager console
2. Click "Store a new secret"
3. Select "Other type of secret"
4. Enter the secret value in the following JSON format:
```json
{
    "repositories": [
        {
            "repository": "owner1/repo1",
            "accesstoken": "github_access_token_xxx"
        }
    ],
    "defaulttoken": "github_access_token_yyy"
}
```
5. Name the secret `GitHubTrafficAccessTokens`
6. Complete the secret creation process

### 2. Deploy the Solution

#### Option A: Using AWS Console

1. Go to AWS CloudFormation console
2. Click "Create stack" and choose "With new resources (standard)"
3. Upload the template file or paste its contents
4. Fill in the parameters:
   - `GitHubRepositories`: Semicolon-separated list of repositories (e.g., "owner1/repo1;owner2/repo2")
   - `LambdaTimeout`: Time in seconds before Lambda function times out (default: 300)
   - `LambdaMemory`: Memory allocation for Lambda function in MB (default: 128)
   - `LogRetentionDays`: Number of days to retain CloudWatch logs (default: 30)
5. Click through the remaining steps and create the stack

#### Option B: Using AWS CLI

```bash
aws cloudformation create-stack \
  --stack-name github-traffic-tracker \
  --template-body file://templates/github-traffic-tracker.yaml \
  --parameters \
    ParameterKey=GitHubRepositories,ParameterValue="owner1/repo1;owner2/repo2" \
    ParameterKey=LambdaTimeout,ParameterValue=300 \
    ParameterKey=LambdaMemory,ParameterValue=128 \
    ParameterKey=LogRetentionDays,ParameterValue=30 \
  --capabilities CAPABILITY_IAM
```

## Monitoring and Metrics

### CloudWatch Metrics

The solution publishes the following metrics to CloudWatch:

Namespace: `GitHubTrafficTracker`

Metrics:
- `views`: Page views statistics
- `clones`: Repository clone statistics

Dimensions:
- `type`: Either "count" or "uniques"
- `repository`: Repository name in format "owner/repo"

### CloudWatch Logs

Logs are stored in two locations:
1. `/aws/lambda/GitHubTrafficTracker`: Lambda function logs
2. `github-traffic-tracker`: Raw GitHub traffic data logs

## Updating Repository List

To update the list of tracked repositories:

1. Go to AWS Systems Manager Parameter Store
2. Find the parameter named `GitHubTrafficRepos`
3. Click "Edit"
4. Enter new semicolon-separated list of repositories
5. Click "Save changes"

Alternatively, using AWS CLI:
```bash
aws ssm put-parameter \
  --name GitHubTrafficRepos \
  --type String \
  --value "owner1/repo1;owner2/repo2" \
  --overwrite
```

## Updating Access Tokens

To update GitHub access tokens:

1. Go to AWS Secrets Manager console
2. Find the secret named `GitHubTrafficAccessTokens`
3. Click "Retrieve secret value"
4. Click "Edit"
5. Update the JSON with new tokens
6. Click "Save"

## Troubleshooting

### Common Issues

1. **Lambda Function Timeout**
   - Symptom: Function execution incomplete
   - Solution: Increase the `LambdaTimeout` parameter

2. **Invalid Repository Format**
   - Symptom: Error logs in CloudWatch
   - Solution: Ensure repositories are in "owner/repo" format

3. **Access Token Issues**
   - Symptom: 403 errors in CloudWatch logs
   - Solution: Verify token permissions and expiration

### Checking Logs

To view execution logs:
1. Go to CloudWatch console
2. Select "Log groups"
3. Check either:
   - `/aws/lambda/GitHubTrafficTracker` for function logs
   - `github-traffic-tracker` for traffic data

## Cleanup

To remove the solution:

1. Using AWS Console:
   - Go to CloudFormation console
   - Select the stack
   - Click "Delete"

2. Using AWS CLI:
```bash
aws cloudformation delete-stack --stack-name github-traffic-tracker
```

Note: The `GitHubTrafficAccessTokens` secret is not managed by CloudFormation and must be deleted separately if desired.

## Security Considerations

- The solution uses AWS Secrets Manager to securely store GitHub access tokens
- IAM roles follow the principle of least privilege
- All data is encrypted at rest using AWS default encryption
- CloudWatch logs are retained according to the specified retention period

## License

This project is licensed under the MIT License - see the LICENSE file for details.
