"""
FuelTrack Backend — FastAPI + AWS DynamoDB
==========================================
Architecture:
  Docker Container (Uvicorn + FastAPI)  →  AWS DynamoDB

Runs as a long-lived HTTP server instead of a Lambda function.
The DynamoDB table schema is identical to the Lambda version so
the same table can be reused without any migrations.

DynamoDB table schema
---------------------
  Table name    : FuelEntries
  Partition key : userId   (String)
  Sort key      : entryId  (String)
  GSI           : UserDateIndex  (userId PK, date SK)

Environment variables
---------------------
  DYNAMODB_TABLE      FuelEntries          (required)
  AWS_REGION          ap-south-1           (default)
  AWS_ACCESS_KEY_ID   <your key>           (or use IAM role / instance profile)
  AWS_SECRET_ACCESS_KEY <your secret>
  DYNAMODB_ENDPOINT   http://dynamodb:8000 (only for local DynamoDB Local)
  ALLOWED_ORIGIN      *                    (CORS — restrict in production)
  PORT                8000                 (Uvicorn listen port)
"""

import os
import uuid
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator, model_validator

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("fueltrack")

# ──────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────
app = FastAPI(
    title="FuelTrack API",
    description="Fuel economy tracking service backed by AWS DynamoDB.",
    version="2.0.0",
)

# CORS — allow the HTML frontend to call this API from any origin (dev default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("ALLOWED_ORIGIN", "*")],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "x-api-key"],
)

# ──────────────────────────────────────────────
# DynamoDB — single resource shared across requests
# ──────────────────────────────────────────────
def _build_dynamodb_resource():
    kwargs = dict(region_name=os.environ.get("AWS_REGION", "ap-south-1"))
    endpoint = os.environ.get("DYNAMODB_ENDPOINT")          # set only for DynamoDB Local
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.resource("dynamodb", **kwargs)


_dynamodb = _build_dynamodb_resource()
_TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "FuelEntries")


def get_table():
    return _dynamodb.Table(_TABLE_NAME)


# ──────────────────────────────────────────────
# Decimal helpers (DynamoDB stores numbers as Decimal)
# ──────────────────────────────────────────────
def to_decimal(value: float) -> Decimal:
    return Decimal(str(value))


def serialise_item(item: dict) -> dict:
    """Recursively convert Decimal → float so FastAPI can JSON-serialise it."""
    out = {}
    for k, v in item.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, dict):
            out[k] = serialise_item(v)
        else:
            out[k] = v
    return out


# ──────────────────────────────────────────────
# Pydantic models
# ──────────────────────────────────────────────
class EntryCreate(BaseModel):
    userId:  str
    vehicle: str
    date:    str        # YYYY-MM-DD
    tripKm:  float
    fuel:    float
    cost:    float

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be in YYYY-MM-DD format")
        return v

    @field_validator("fuel")
    @classmethod
    def fuel_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("fuel must be greater than 0")
        return v

    @field_validator("tripKm", "cost")
    @classmethod
    def non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("value must be ≥ 0")
        return v


class EntryResponse(BaseModel):
    entryId:   str
    userId:    str
    vehicle:   str
    date:      str
    tripKm:    float
    fuel:      float
    cost:      float
    economy:   float
    createdAt: str


class EntryListResponse(BaseModel):
    items: list[EntryResponse]
    count: int


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.get("/health", tags=["Meta"])
def health_check():
    """Liveness probe — used by Docker HEALTHCHECK and load balancers."""
    return {
        "status": "ok",
        "service": "FuelTrack",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/entries", status_code=201, response_model=EntryResponse, tags=["Entries"])
def create_entry(payload: EntryCreate):
    """
    Record a new refueling event.
    Economy (km/L) is computed server-side from tripKm ÷ fuel.
    """
    economy  = round(payload.tripKm / payload.fuel, 2)
    entry_id = str(uuid.uuid4())
    now_iso  = datetime.now(timezone.utc).isoformat()

    item = {
        "userId":    payload.userId,
        "entryId":   entry_id,
        "vehicle":   payload.vehicle,
        "date":      payload.date,
        "tripKm":    to_decimal(payload.tripKm),
        "fuel":      to_decimal(payload.fuel),
        "cost":      to_decimal(payload.cost),
        "economy":   to_decimal(economy),
        "createdAt": now_iso,
    }

    try:
        get_table().put_item(Item=item)
        logger.info("Created entry %s for user %s", entry_id, payload.userId)
    except ClientError as exc:
        logger.error("DynamoDB put_item failed: %s", exc)
        raise HTTPException(status_code=500, detail="Could not save entry to DynamoDB")

    return serialise_item(item)


@app.get("/entries", response_model=EntryListResponse, tags=["Entries"])
def list_entries(
    userId:  str           = Query(...,  description="User ID to fetch entries for"),
    vehicle: Optional[str] = Query(None, description="Filter by vehicle type"),
    month:   Optional[str] = Query(None, description="Filter by month, format YYYY-MM"),
):
    """
    Return all refueling entries for a user.
    Optionally filter by vehicle type and/or month.
    """
    table    = get_table()
    key_cond = Key("userId").eq(userId)

    try:
        if month:
            # Use the GSI to efficiently filter by date prefix
            result = table.query(
                IndexName="UserDateIndex",
                KeyConditionExpression=key_cond & Key("date").begins_with(month),
            )
        else:
            result = table.query(
                KeyConditionExpression=key_cond,
                ScanIndexForward=False,
            )
    except ClientError as exc:
        logger.error("DynamoDB query failed: %s", exc)
        raise HTTPException(status_code=500, detail="Could not fetch entries from DynamoDB")

    items = [serialise_item(i) for i in result.get("Items", [])]

    if vehicle:
        items = [i for i in items if i.get("vehicle") == vehicle]

    items.sort(key=lambda x: x.get("date", ""), reverse=True)
    logger.info("Listed %d entries for user %s", len(items), userId)
    return {"items": items, "count": len(items)}


@app.delete("/entries/{entryId}", tags=["Entries"])
def delete_entry(
    entryId: str = Path(..., description="UUID of the entry to delete"),
    userId:  str = Query(..., description="Owner's user ID"),
):
    """
    Delete a single refueling entry by its ID.
    Returns 404 if the entry does not exist or belongs to a different user.
    """
    try:
        get_table().delete_item(
            Key={"userId": userId, "entryId": entryId},
            ConditionExpression=Attr("entryId").exists(),
        )
        logger.info("Deleted entry %s for user %s", entryId, userId)
        return {"deleted": True, "entryId": entryId}

    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise HTTPException(status_code=404, detail="Entry not found")
        logger.error("DynamoDB delete_item failed: %s", exc)
        raise HTTPException(status_code=500, detail="Could not delete entry from DynamoDB")


# ──────────────────────────────────────────────
# Table bootstrap helper (called from entrypoint.sh on first run)
# ──────────────────────────────────────────────
def create_table_if_missing():
    """
    Create the DynamoDB table when using DynamoDB Local.
    Safe to call repeatedly — skips silently if the table already exists.
    In production (real AWS), create the table with CDK/SAM/Terraform instead.
    """
    if not os.environ.get("DYNAMODB_ENDPOINT"):
        logger.info("Skipping table bootstrap — using real AWS DynamoDB.")
        return

    client = _dynamodb.meta.client
    try:
        client.describe_table(TableName=_TABLE_NAME)
        logger.info("Table '%s' already exists.", _TABLE_NAME)
    except client.exceptions.ResourceNotFoundException:
        logger.info("Creating table '%s' in DynamoDB Local…", _TABLE_NAME)
        client.create_table(
            TableName=_TABLE_NAME,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "userId",  "AttributeType": "S"},
                {"AttributeName": "entryId", "AttributeType": "S"},
                {"AttributeName": "date",    "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "userId",  "KeyType": "HASH"},
                {"AttributeName": "entryId", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "UserDateIndex",
                    "KeySchema": [
                        {"AttributeName": "userId", "KeyType": "HASH"},
                        {"AttributeName": "date",   "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        )
        logger.info("Table '%s' created.", _TABLE_NAME)


@app.on_event("startup")
def on_startup():
    create_table_if_missing()


# ──────────────────────────────────────────────
# Dev entrypoint  (python main.py)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
        log_level="info",
    )
