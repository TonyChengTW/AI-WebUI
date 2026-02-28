#!/bin/bash
docker compose down ; docker rmi ai_webui-ai-webui:latest ; docker compose up -d --build
