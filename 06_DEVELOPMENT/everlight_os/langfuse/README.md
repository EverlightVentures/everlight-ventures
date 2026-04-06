Langfuse should run on the larger Oracle core host, not the 1 GB trading box.

Use `OBS_PROFILE=core ../deploy_oracle_observability.sh langfuse` to upload the compose file, create a remote `.env` if missing, and start the stack with the first available remote runtime (`docker compose`, `podman compose`, or `podman-compose`).

To deploy the split topology in one step, run `../../../03_AUTOMATION_CORE/01_Scripts/deploy_observability_topology.sh`.

Default URL: `http://<core-oracle-ip>:3100`
