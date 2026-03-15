Netdata runs on Oracle via `docker compose`.

Use `../deploy_oracle_observability.sh netdata` to upload the compose file, create a remote `.env` if missing, and start the container with `sudo docker compose`.

Default URL: `http://<oracle-ip>:19999`
