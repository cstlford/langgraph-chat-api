import requests
from typing import Any, Protocol
import io
import os
import sys
import time
import asyncio
import contextlib
import uuid
import math
import json
import re
import random
import statistics
import itertools
import collections
import datetime
import decimal
import fractions
import csv
import gzip
import zipfile
import tarfile
import textwrap
import pprint
import base64
import hashlib
import hmac
import urllib.parse as urlparse
import pathlib
import numpy as np
import seaborn as sns
import pandas as pd
from fastapi import HTTPException

import matplotlib.pyplot as plt
from config import logger, TEMP_IMAGE_DIR


class ExecuteSQLCallable(Protocol):
    def __call__(self, sql: str, timeout: int = ...) -> pd.DataFrame: ...


def execute_sql(sql: str, database: str, timeout: int = 60) -> pd.DataFrame:
    """Execute SQL query via external API"""
    try:
        response = requests.post(
            "http://host.docker.internal:8000/api/db/query",
            json={"sql": sql, "database": database},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and len(data) == 0:
            logger.warning("SQL query returned empty result set")
            return pd.DataFrame()
        df = pd.DataFrame(data)
        logger.info(f"SQL query returned {len(df)} rows")
        return df
    except requests.exceptions.HTTPError as http_error:
        status_code = (
            http_error.response.status_code if http_error.response is not None else 502
        )
        logger.error(f"HTTP error executing SQL: {http_error}")
        raise HTTPException(status_code=status_code, detail=str(http_error))
    except requests.exceptions.RequestException as req_error:
        logger.error(f"Request error executing SQL: {req_error}")
        raise HTTPException(status_code=502, detail=str(req_error))
    except Exception as unexpected_error:
        logger.error(f"Unexpected error executing SQL: {unexpected_error}")
        raise HTTPException(status_code=500, detail=str(unexpected_error))


def capture_matplotlib_figures() -> list[str]:
    """Capture all matplotlib figures as files in /tmp and return their URLs"""
    images = []
    try:
        figures = plt.get_fignums()
        for fig_num in figures:
            try:
                fig = plt.figure(fig_num)
                if not fig.axes:
                    continue
                image_id = str(uuid.uuid4())
                image_path = os.path.join(TEMP_IMAGE_DIR, f"{image_id}.png")
                fig.savefig(
                    image_path,
                    format="png",
                    dpi=150,
                    bbox_inches="tight",
                    facecolor="white",
                    edgecolor="none",
                )
                image_url = f"/images/temp/{image_id}.png"
                images.append(image_url)
            except Exception as e:
                logger.warning(f"Failed to save figure {fig_num}: {str(e)}")
        plt.close("all")
    except Exception as e:
        logger.error(f"Error capturing matplotlib figures: {str(e)}")
    return images


def capture_objects(local_vars: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Capture created objects, including DataFrame contents.

    For DataFrames we save a CSV into TEMP_IMAGE_DIR and return a file URL reference.
    Returns a tuple: (objects_dict, list_of_file_urls).
    """
    objects = {}
    files: list[str] = []
    excluded_keys = {
        "execute_sql",
        "plt",
        "np",
        "pd",
        "sns",
        "requests",
        "os",
        "sys",
        "io",
        "math",
        "json",
        "re",
        "random",
        "statistics",
        "itertools",
        "collections",
        "datetime",
        "decimal",
        "fractions",
        "csv",
        "gzip",
        "zipfile",
        "tarfile",
        "textwrap",
        "pprint",
        "base64",
        "hashlib",
        "hmac",
        "urlparse",
        "pathlib",
        "__builtins__",
        "__name__",
        "__doc__",
        "__package__",
        "matplotlib",
        "numpy",
        "pandas",
        "seaborn",
    }
    try:
        os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)
    except Exception:
        pass

    for key, value in local_vars.items():
        if key.startswith("_") or key in excluded_keys or callable(value):
            continue
        try:
            if isinstance(value, (str, int, float, bool, type(None))):
                objects[key] = value
            elif isinstance(value, (list, tuple, set)):
                objects[key] = (
                    list(value)[:100]
                    if len(value) <= 100
                    else f"{type(value).__name__} with {len(value)} items"
                )
            elif isinstance(value, dict):
                objects[key] = (
                    dict(list(value.items())[:50])
                    if len(value) <= 50
                    else f"Dict with {len(value)} keys"
                )
            elif isinstance(value, pd.DataFrame):
                df_info = {
                    "type": "DataFrame",
                    "shape": [value.shape[0], value.shape[1]],
                    "columns": list(value.columns),
                    "data": value.head(5).to_dict(orient="records"),
                }
                try:
                    file_id = str(uuid.uuid4())
                    file_path = os.path.join(TEMP_IMAGE_DIR, f"{file_id}.csv")
                    value.to_csv(file_path, index=False)
                    file_url = f"/files/temp/{file_id}.csv"
                    files.append(file_url)
                    df_info["file"] = file_url

                except Exception as e:
                    df_info["file_error"] = str(e)[:500]
                objects[key] = df_info
            elif isinstance(value, np.ndarray):
                objects[key] = {
                    "type": "Array",
                    "shape": list(value.shape),
                    "dtype": str(value.dtype),
                    "data": (
                        value.tolist()[:100]
                        if value.size <= 100
                        else f"Array with {value.size} elements"
                    ),
                }
            else:
                objects[key] = f"{type(value).__name__}: {str(value)[:500]}"
        except Exception as e:
            objects[key] = f"<Error capturing object: {str(e)}>"
    return objects, files


async def execute_code_async(code: str, bound_execute_sql: ExecuteSQLCallable) -> dict:
    """Execute Python code asynchronously"""
    timeout = 60

    result = {
        "output": "",
        "errors": "",
        "images": [],
        "objects": {},
        "files": [],
        "execution_time": 0.0,
    }
    start_time = time.time()

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    exec_env = {
        "__builtins__": __builtins__,
        "__name__": "__main__",
        # Data libs
        "pd": pd,
        "np": np,
        # Plotting
        "plt": plt,
        "sns": sns,
        # HTTP/IO
        "requests": requests,
        "io": io,
        # System/OS
        "os": os,
        "sys": sys,
        "pathlib": pathlib,
        # Math & stats
        "math": math,
        "random": random,
        "statistics": statistics,
        "decimal": decimal,
        "fractions": fractions,
        # Text, parsing, encoding
        "json": json,
        "re": re,
        "textwrap": textwrap,
        "pprint": pprint,
        "base64": base64,
        "hashlib": hashlib,
        "hmac": hmac,
        # Datetime & utils
        "datetime": datetime,
        "itertools": itertools,
        "collections": collections,
        # File formats & compression
        "csv": csv,
        "gzip": gzip,
        "zipfile": zipfile,
        "tarfile": tarfile,
        # URL utilities
        "urlparse": urlparse,
        # Bound helpers
        "execute_sql": bound_execute_sql,
    }

    try:
        with (
            contextlib.redirect_stdout(stdout_buffer),
            contextlib.redirect_stderr(stderr_buffer),
        ):
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, lambda: exec(code, exec_env, exec_env)),
                timeout=timeout,
            )
        result["output"] = stdout_buffer.getvalue()
        result["errors"] = stderr_buffer.getvalue()
        result["images"] = capture_matplotlib_figures()
        objs, files = capture_objects(exec_env)
        result["objects"] = objs
        result["files"] = files
        result["status"] = "success"
    except asyncio.TimeoutError:
        result["status"] = "timeout"
        result["errors"] = f"Code execution timed out after {timeout} seconds"
        logger.warning("Execution timed out")
    except Exception as e:
        result["status"] = "error"
        result["errors"] = f"Error: {str(e)}"
        logger.error(f"Execution failed: {str(e)}")
    finally:
        stdout_buffer.close()
        stderr_buffer.close()
        result["execution_time"] = time.time() - start_time
    return result
