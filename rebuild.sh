#!/bin/bash
docker compose down ; docker rmi ai_webui-webui:latest ; docker compose up -d --build
