# System One CPU classification

This service runs pinned [Von](https://github.com/wfzyx/von) weights on a CPU and answers choice, yes/no, and score questions over HTTP. The Docker image includes the weights, so startup needs no model download.

## Run the image

```sh
docker run --rm -p 8000:8000 --cpus=4 --memory=8g \
  ghcr.io/agmangas/system-one-classification:latest
```

The image works on `linux/amd64` and `linux/arm64`. 

- `GET /ready`: Ready when the model loads.
- `GET /health`: Checks app up.
- `GET /v1/models`: Lists model, backend, versions.
- `/docs`: OpenAPI.
- Use `SYSTEM_ONE_API_KEY` to require auth.

Send `model`, `state`, and `questions` to `POST /v1/systemone`. The response gives `answers` and `usage`. The model ID is `system-one-cpu`. 

- Each choice/score question takes one model pass.
- Yes/no (`noul`) with criteria: one pass. Without criteria: two passes.
- Optional chains are off.

This example uses six material labels and an `unknown` rejection result:

```sh
curl -sS http://localhost:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "system-one-cpu",
    "state": "Misspelled material name: alumnium",
    "questions": {
      "material": {
        "type": "choice",
        "instructions": "Classify the material named by the input.",
        "criteria": {
          "concrete": "concrete",
          "steel": "steel",
          "timber": "timber",
          "brick": "brick",
          "glass": "glass",
          "stone": "stone",
          "unknown": "Aluminum, plastic, copper, or other unlisted materials"
        }
      }
    }
  }'
```
