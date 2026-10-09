# AnnaSetu on AWS (SAM, ap-south-1)

`template.yaml` defines everything in CLAUDE.md Section 15: HTTP API (10 rps, `x-api-key` checked by a Lambda
authorizer), Lambdas `advisor`, `voice`, `ingest` (EventBridge Scheduler, 21:00 Asia/Kolkata) and `authorizer`,
DynamoDB `MarketDay` / `MarketRisk` / `Outlets` / `Plans` (on-demand), private S3 data and audio buckets (audio
deleted after 1 day), Amazon Location place index and route calculator, and a CloudWatch alarm on ingest errors.
Each function gets its own least-privilege role (Section 15.2).

The build (`Makefile`, `BuildMethod: makefile`) packages only `backend/` (without tests), `config/` and `data/`
from the repo root. No third-party Python packages are deployed; boto3 comes with the Lambda runtime.

No credentials, account IDs or model IDs are committed. `samconfig.toml` is git-ignored: `sam deploy --guided`
writes your account's choices there.

## Prerequisites

- AWS account, region `ap-south-1`, AWS CLI configured with the team's credentials.
- AWS SAM CLI (open source; `pip install aws-sam-cli` or the installer) and `make`.

## Deploy (CLAUDE.md Section 15.4)

1. **Budget alert first.** Billing console -> Budgets -> create a monthly cost budget (for example USD 10) with an
   email alert at 80% and 100%.
2. **Bedrock model access (optional; without it the app uses templates and the rule parser).**
   Bedrock console in ap-south-1 -> Model access -> enable Amazon Nova Lite (CLAUDE.md D23; any model that supports
   the Converse API works, e.g. a Claude Haiku model if your account has Anthropic access). Check in the console that
   it is offered in ap-south-1 and whether it is invoked on demand or only through an APAC cross-region inference
   profile. Test one prompt in the playground. Note:
   - the ID you will invoke (model ID, or inference profile ID) -> parameter `BedrockModelId`;
   - the ARN(s) to allow -> parameter `BedrockModelArns` (comma-separated). On-demand:
     `arn:aws:bedrock:ap-south-1::foundation-model/<model-id>`. Inference profile: the profile ARN
     `arn:aws:bedrock:ap-south-1:<account>:inference-profile/<profile-id>` plus the foundation-model ARN in each
     region the profile routes to (`arn:aws:bedrock:*::foundation-model/<model-id>`).
   Leave both empty to keep Bedrock off. `config/model.json` keeps `model_id: null`; the deployed value comes from
   the `BEDROCK_MODEL_ID` environment variable.
3. **Parameters in SSM (SecureString, default AWS managed key):**
   ```
   aws ssm put-parameter --region ap-south-1 --type SecureString --name /annasetu/datagov_key  --value '<data.gov.in key>'
   aws ssm put-parameter --region ap-south-1 --type SecureString --name /annasetu/app_api_key --value "$(openssl rand -hex 24)"
   ```
4. **Build and deploy** from `infra/`:
   ```
   sam build && sam deploy --guided
   ```
   Stack name `annasetu`, region `ap-south-1`, `NameSuffix` = a short lowercase team suffix, optional
   `AlarmEmail` (confirm the SNS email), Bedrock parameters from step 2. Outputs: `ApiUrl`, table and bucket names, `PlaceIndexName`, `RouteCalculatorName`.
5. **Geocode markets** (writes lat/lon and confidence into `config/markets.json`; markets with
   `"coord_override": true` keep theirs). Review the diff, then commit:
   ```
   python scripts/geocode_markets.py --index <PlaceIndexName>
   ```
6. **Seed** Outlets and MarketDay (from `data/snapshot/`) and upload the snapshot to `s3://<DataBucket>/snapshot/`:
   ```
   python scripts/seed.py --stack annasetu
   ```
7. **Run ingest once** and check MarketRisk rows:
   ```
   aws lambda invoke --region ap-south-1 --function-name <IngestFunctionName> --payload '{}' out.json && cat out.json
   aws dynamodb query --region ap-south-1 --table-name <MarketRiskTable> \
     --key-condition-expression "crop = :c" --expression-attribute-values '{":c":{"S":"tomato"}}'
   ```
   Pass `{"as_of_date": "2025-02-07"}` as the payload to compute risk for a replay day from seeded history.
8. **App:** set `EXPO_PUBLIC_API_URL` = `ApiUrl` and `EXPO_PUBLIC_API_KEY` = the `/annasetu/app_api_key` value
   in the app's env (not committed), then `eas build -p android --profile preview`.
9. **Smoke test** on a real Android phone: one typed and one voice recommendation.

## Local runs

```
sam build && sam local start-api      # needs Docker; set DATA_SOURCE=snapshot via --env-vars for offline replay
python -m pytest backend/tests -q     # stubbed AWS clients, no network
```

## Notes and limits

- Polly has no Kannada voice: `POST /speak` with `language: "kn"` returns 422 `speak_language_unsupported`, and
  the app shows text only. Hindi and Indian English use the neural voice Kajal.
- Transcribe batch jobs run in hi-IN, kn-IN and en-IN; `/voice/parse` waits up to 20 s for the job.
- Ingest re-pulls the last 14 days from CEDA for markets in `config/markets.json` and computes MarketRisk from
  MarketDay history (seed it first, step 6). Any failed market makes the run raise, which trips the alarm.
- The API key is a demo control, not user authentication (no user accounts, CLAUDE.md Section 21).
