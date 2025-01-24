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

1. An AWS account with access to:
   - AWS CloudShell or AWS CLI
   - AWS SAM CLI (pre-installed in CloudShell)
   - GitHub repositories you want to track
   
2. A GitHub personal access token with the following permissions:
   - `repo` scope for private repositories
   - `public_repo` scope for public repositories

## Deployment Instructions

### 1. Create GitHub Access Token Secret

Before deploying the SAM template, create a secret in AWS Secrets Manager:

1. Go to AWS Secrets Manager console
2. Click "Store a new secret"
3. Select "Other type of secret"
4. Enter the secret value in the following JSON format:
```json
{
    "repositories": [
        {
            "repository": "owner1/repo1",
            "accesstoken": "github_pat_xxx"
        }
    ],
    "defaulttoken": "github_pat_yyy"
}
```
5. Name the secret `GitHubTrafficAccessTokens`
6. Complete the secret creation process

### 2. Deploy Using AWS CloudShell

1. Open AWS CloudShell:
   - Go to AWS Management Console
   - Click the CloudShell icon in the top navigation bar

2. Clone and prepare the repository:
```bash
# Clone the repository
git clone https://github.com/carlos-aws/repo-traffic-tracker.git
cd github-traffic-tracker

# Build the SAM application
sam build
```

3. Deploy the application:
```bash
sam deploy --guided
```

4. During the guided deployment, you'll be prompted for parameters:
   - Stack Name: `github-traffic-tracker` (recommended)
   - AWS Region: Choose your preferred region
   - Parameter GitHubRepositories: Enter semicolon-separated list of repositories (e.g., "owner1/repo1;owner2/repo2")
   - Parameter LambdaTimeout: Enter timeout in seconds (default: 300)
   - Parameter LambdaMemory: Enter memory in MB (default: 128)
   - Parameter LogRetentionDays: Enter log retention period (default: 1827)
   - Confirm changes before deploy: Yes
   - Allow SAM CLI IAM role creation: Yes
   - Disable rollback: No
   - Save arguments to configuration file: Yes
   - SAM configuration file: samconfig.toml
   - SAM configuration environment: default

## Monitoring and Metrics

### CloudWatch Metrics

The solution publishes the following metrics:

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

## Managing the Solution

### Updating Repository List

1. Open AWS Systems Manager Console
2. Go to Parameter Store
3. Find parameter named `GitHubTrafficRepos`
4. Click "Edit"
5. Update the semicolon-separated list
6. Click "Save changes"

Or using CloudShell:
```bash
aws ssm put-parameter \
  --name GitHubTrafficRepos \
  --type String \
  --value "owner1/repo1;owner2/repo2" \
  --overwrite
```

### Updating Access Tokens

1. Open AWS Secrets Manager Console
2. Find secret named `GitHubTrafficAccessTokens`
3. Click "Retrieve secret value"
4. Click "Edit"
5. Update the JSON with new tokens
6. Click "Save"

## Troubleshooting

### Common Issues

1. **Lambda Function Timeout**
   - Symptom: Function execution incomplete
   - Solution: Increase the `LambdaTimeout` parameter during deployment

2. **Invalid Repository Format**
   - Symptom: Error logs in CloudWatch
   - Solution: Ensure repositories are in "owner/repo" format

3. **Access Token Issues**
   - Symptom: 403 errors in CloudWatch logs
   - Solution: Verify token permissions and expiration

### Checking Logs

Using CloudShell:
```bash
# View Lambda function logs
aws logs tail /aws/lambda/GitHubTrafficTracker --follow

# View traffic data logs
aws logs tail github-traffic-tracker --follow
```

Or through AWS Console:
1. Open CloudWatch Console
2. Go to Log Groups
3. Select either:
   - `/aws/lambda/GitHubTrafficTracker`
   - `github-traffic-tracker`

## Cleanup

To remove all resources created by this solution:

Using CloudShell:
```bash
sam delete
```

Or manually:
1. Open CloudFormation Console
2. Select stack named `github-traffic-tracker`
3. Click "Delete"
4. Click "Delete stack"

Note: The `GitHubTrafficAccessTokens` secret is not managed by SAM and must be deleted separately if desired.

## Security Considerations

- GitHub access tokens are stored securely in AWS Secrets Manager
- IAM roles follow the principle of least privilege
- All data is encrypted at rest using AWS default encryption
- CloudWatch logs are retained according to specified retention period
- Function runs within a VPC-isolated environment

## License

This project is licensed under the MIT License - see the LICENSE file for details.
