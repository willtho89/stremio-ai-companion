# Dynamic Worker Configuration for Stremio AI Companion

This document explains how to configure the number of uvicorn workers for the Stremio AI Companion application.

## Overview

The Stremio AI Companion now supports dynamic worker configuration, allowing you to:

1. Automatically determine the optimal number of workers based on available CPU cores
2. Manually specify a fixed number of workers via an environment variable

This feature helps optimize performance based on your server's resources and workload.

## How It Works

The application uses an entrypoint script (`entrypoint.sh`) that:

1. Checks if the `UVICORN_WORKERS` environment variable is set
2. If not set or set to `0`, calculates the optimal number of workers based on available CPU cores
3. Applies reasonable limits (minimum 1, maximum 8 workers)
4. Executes uvicorn with the calculated number of workers

## Configuration Options

### Automatic Worker Configuration (Default)

By default, the application will automatically calculate the optimal number of workers based on the available CPU cores:

```bash
# No environment variable set, or set to 0
UVICORN_WORKERS=0 docker-compose up
```

The calculation logic:
- Uses the number of CPU cores for I/O bound applications (like this FastAPI app)
- Sets a minimum of 1 worker
- Sets a maximum of 8 workers to prevent excessive resource usage

### Manual Worker Configuration

To manually specify the number of workers, set the `UVICORN_WORKERS` environment variable:

```bash
# Set a specific number of workers (e.g., 4)
UVICORN_WORKERS=4 docker-compose up
```

## Recommendations

- For most deployments, the automatic configuration is recommended
- For high-traffic deployments, consider setting a specific number of workers based on your server's resources
- For development or low-resource environments, setting `UVICORN_WORKERS=1` may be appropriate

## Considerations

When using multiple workers:

1. **Memory Usage**: Each worker is a separate process with its own memory footprint, so monitor your container's memory usage.

2. **Database Connections**: If your app uses a database, ensure your connection pool is configured appropriately for multiple workers.

3. **Shared State**: Workers don't share memory, so any in-memory state won't be shared between workers. Use external storage (like Redis) for shared state if needed.

## Troubleshooting

If you encounter issues with the worker configuration:

1. Check the container logs for messages about worker configuration
2. Verify that the `UVICORN_WORKERS` environment variable is set correctly
3. Try setting a specific number of workers to rule out issues with the automatic calculation