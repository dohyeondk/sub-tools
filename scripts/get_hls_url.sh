#!/usr/bin/env bash

HLS_URL=$(curl "https://api.life.church/v2/messages?key=ecafba80c4f683b3b0e70d9c8de71dae&include=series&quantity=1&type=sermon" | jq '.[0].formats[] | select(.name == "download_video") | .url' -r)

echo "$HLS_URL"

# uv run sub-tools -i "$HLS_URL" --overwrite
