Netdata should stay on the lightweight bot host so runtime health stays visible without crowding the trading process.

Use `OBS_PROFILE=bot ../deploy_oracle_observability.sh netdata` to upload the compose file, create a remote `.env` if missing, and start the container with the first available remote runtime (`docker compose`, `podman compose`, or `podman-compose`).

To deploy the split topology in one step, run `../../../03_AUTOMATION_CORE/01_Scripts/deploy_observability_topology.sh`.

Default URL: `http://<bot-oracle-ip>:19999`
