# /// script
# dependencies = [
#   "mcp",
#   "requests",
#   "python-dotenv"
# ]
# ///
import asyncio
import json
import logging
import sys
from typing import Any, Optional
import os
from dotenv import load_dotenv
import requests

import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Log to stderr — stdout is reserved for the MCP JSON-RPC transport.
logging.basicConfig(
    level=os.getenv("ASHBY_MCP_LOG_LEVEL", "INFO"),
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ashby-mcp")

class AshbyClient:
    """Handles Ashby operations and caching."""
    
    def __init__(self):
        self.api_key: Optional[str] = None
        self.base_url = "https://api.ashbyhq.com"
        self.headers = {}

    def connect(self) -> bool:
        """Establishes connection to Ashby using API key from environment variables.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.api_key = os.getenv('ASHBY_API_KEY')
            if not self.api_key:
                raise ValueError("ASHBY_API_KEY environment variable not set")
            
            self.headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            return True
        except Exception as e:
            logger.error("Ashby connection failed: %s", e)
            return False

    def _make_request(self, endpoint: str, method: str = "GET", data: Optional[dict] = None) -> dict:
        """Make a request to the Ashby API.
        
        Args:
            endpoint (str): The API endpoint to call
            method (str): HTTP method (GET, POST, etc.)
            data (Optional[dict]): Data to send with the request
            
        Returns:
            dict: Response from the API
        """
        if not self.api_key:
            raise ValueError("Ashby connection not established")
            
        url = f"{self.base_url}{endpoint}"
        logger.debug("Ashby API request: %s %s", method, endpoint)
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            json=data,
            auth=(self.api_key, ""),
        )
        if response.status_code in (401, 403):
            logger.warning(
                "Ashby API auth failure: %s %s -> %s",
                method, endpoint, response.status_code,
            )
        elif response.status_code >= 400:
            logger.error(
                "Ashby API error: %s %s -> %s",
                method, endpoint, response.status_code,
            )
        response.raise_for_status()
        return response.json()

# Create a server instance
server = Server("ashby-mcp")

# Load environment variables
load_dotenv()

# Configure with Ashby API key from environment variables
ashby_client = AshbyClient()
if not ashby_client.connect():
    logger.error("Failed to initialize Ashby connection")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools for Ashby operations.
    """
    return [
        # Candidate Management Tools
        types.Tool(
            name="create_candidate",
            description="Creates a new candidate in Ashby",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Candidate's full name"},
                    "email": {"type": "string", "description": "Candidate's email address"},
                    "phone_number": {"type": "string", "description": "Candidate's phone number"}
                },
                "required": ["name", "email"]
            }
        ),
        types.Tool(
            name="search_candidates",
            description="Search for candidates by email and/or name",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Candidate's email"},
                    "name": {"type": "string", "description": "Candidate's name"}
                }
            }
        ),
        types.Tool(
            name="list_candidates",
            description="List candidates with pagination and filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "Page number", "default": 1},
                    "page_size": {"type": "integer", "description": "Results per page", "default": 100},
                    "filters": {
                        "type": "object",
                        "description": "Additional filters to apply"
                    }
                }
            }
        ),
        
        # Job Management Tools
        types.Tool(
            name="create_job",
            description="Creates a new job posting",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Job title"},
                    "description": {"type": "string", "description": "Job description"},
                    "department": {"type": "string", "description": "Department name"},
                    "location": {"type": "string", "description": "Job location"}
                },
                "required": ["title", "description"]
            }
        ),
        types.Tool(
            name="search_jobs",
            description="Search for jobs by title and filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Job title to search for"},
                    "location": {"type": "string", "description": "Filter by location"},
                    "department": {"type": "string", "description": "Filter by department"},
                    "include_unlisted": {"type": "boolean", "description": "Include unlisted jobs"}
                }
            }
        ),
        
        # Application Management Tools
        types.Tool(
            name="create_application",
            description="Creates a new application",
            inputSchema={
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "string", "description": "Candidate ID"},
                    "job_id": {"type": "string", "description": "Job ID"},
                    "source": {"type": "string", "description": "Application source"}
                },
                "required": ["candidate_id", "job_id"]
            }
        ),
        types.Tool(
            name="list_applications",
            description="List applications with pagination and filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "Page number", "default": 1},
                    "page_size": {"type": "integer", "description": "Results per page", "default": 100},
                    "filters": {
                        "type": "object",
                        "description": "Additional filters to apply"
                    }
                }
            }
        ),
        
        # Interview Management Tools
        types.Tool(
            name="create_interview",
            description="Creates a new interview",
            inputSchema={
                "type": "object",
                "properties": {
                    "application_id": {"type": "string", "description": "Application ID"},
                    "interviewer_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of interviewer IDs"
                    },
                    "start_time": {"type": "string", "description": "Interview start time (ISO format)"},
                    "duration": {"type": "integer", "description": "Interview duration in minutes"},
                    "type": {"type": "string", "description": "Interview type"}
                },
                "required": ["application_id", "interviewer_ids", "start_time", "duration"]
            }
        ),
        types.Tool(
            name="list_interviews",
            description="List interviews with filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "application_id": {"type": "string", "description": "Filter by application ID"},
                    "start_date": {"type": "string", "description": "Filter by start date"},
                    "end_date": {"type": "string", "description": "Filter by end date"}
                }
            }
        ),
        
        # Interview Feedback / Scorecard Tools
        types.Tool(
            name="list_feedback",
            description="List all feedback (scorecards) submitted for an application",
            inputSchema={
                "type": "object",
                "properties": {
                    "applicationId": {"type": "string", "description": "The id of the application to fetch feedback for"},
                    "cursor": {"type": "string", "description": "Pagination cursor"},
                    "syncToken": {"type": "string", "description": "Sync token for incremental updates"},
                    "limit": {"type": "integer", "description": "Max results per page"}
                },
                "required": ["applicationId"]
            }
        ),
        types.Tool(
            name="submit_feedback",
            description=(
                "Submit interview feedback (scorecard) for an application. "
                "Use get_feedback_form first to discover field paths and types — "
                "feedbackForm.fieldSubmissions entries reference those paths."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "applicationId": {"type": "string", "description": "The application receiving the feedback"},
                    "formDefinitionId": {"type": "string", "description": "Id of the feedback form definition being submitted"},
                    "feedbackForm": {
                        "type": "object",
                        "description": (
                            "The submitted form, typically shaped as "
                            "{ fieldSubmissions: [{ path, value }, ...] }. "
                            "Value shape depends on field type — e.g. Score: {score: 1-4}, "
                            "RichText: {type: 'PlainText', value: '...'}."
                        )
                    },
                    "userId": {"type": "string", "description": "Credit feedback to this user. Defaults to the API key's user."},
                    "interviewEventId": {"type": "string", "description": "The interview event this feedback is for (required when scoped to a specific interview)."}
                },
                "required": ["applicationId", "formDefinitionId", "feedbackForm"]
            }
        ),
        types.Tool(
            name="list_feedback_forms",
            description="List all feedback form definitions (scorecard templates)",
            inputSchema={
                "type": "object",
                "properties": {
                    "includeArchived": {"type": "boolean", "description": "Include archived forms"},
                    "cursor": {"type": "string", "description": "Pagination cursor"},
                    "syncToken": {"type": "string", "description": "Sync token for incremental updates"},
                    "limit": {"type": "integer", "description": "Max results per page"}
                }
            }
        ),
        types.Tool(
            name="get_feedback_form",
            description="Get a single feedback form definition by id — use to discover field paths/types before submit_feedback",
            inputSchema={
                "type": "object",
                "properties": {
                    "feedbackFormDefinitionId": {"type": "string", "description": "The id of the feedback form to fetch"}
                },
                "required": ["feedbackFormDefinitionId"]
            }
        ),

        # Candidate Notes (read-only)
        types.Tool(
            name="list_candidate_notes",
            description="List all notes on a candidate",
            inputSchema={
                "type": "object",
                "properties": {
                    "candidateId": {"type": "string", "description": "The id of the candidate to fetch notes for"},
                    "includeArchived": {"type": "boolean", "description": "Include archived notes"},
                    "cursor": {"type": "string", "description": "Pagination cursor"},
                    "syncToken": {"type": "string", "description": "Sync token for incremental updates"},
                    "limit": {"type": "integer", "description": "Max results per page"}
                },
                "required": ["candidateId"]
            }
        ),

        # Analytics Tools
        types.Tool(
            name="get_pipeline_metrics",
            description="Get pipeline metrics for jobs",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Filter by job ID"},
                    "date_range": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string", "description": "Start date"},
                            "end": {"type": "string", "description": "End date"}
                        }
                    }
                }
            }
        ),
        
        # Batch Operations
        types.Tool(
            name="bulk_create_candidates",
            description="Create multiple candidates in a single operation",
            inputSchema={
                "type": "object",
                "properties": {
                    "candidates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                                "phone_number": {"type": "string"}
                            },
                            "required": ["name", "email"]
                        }
                    }
                },
                "required": ["candidates"]
            }
        ),
        types.Tool(
            name="bulk_update_applications",
            description="Update multiple applications in a single operation",
            inputSchema={
                "type": "object",
                "properties": {
                    "updates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "application_id": {"type": "string"},
                                "updates": {"type": "object"}
                            },
                            "required": ["application_id", "updates"]
                        }
                    }
                },
                "required": ["updates"]
            }
        ),
        types.Tool(
            name="bulk_schedule_interviews",
            description="Schedule multiple interviews in a single operation",
            inputSchema={
                "type": "object",
                "properties": {
                    "interviews": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "application_id": {"type": "string"},
                                "interviewer_ids": {"type": "array", "items": {"type": "string"}},
                                "start_time": {"type": "string"},
                                "duration": {"type": "integer"},
                                "type": {"type": "string"}
                            },
                            "required": ["application_id", "interviewer_ids", "start_time", "duration"]
                        }
                    }
                },
                "required": ["interviews"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle tool calls by routing to appropriate Ashby API endpoints."""
    try:
        if name == "create_candidate":
            response = ashby_client._make_request(
                "/candidate.create",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Created candidate: {json.dumps(response, indent=2)}")]
            
        elif name == "search_candidates":
            response = ashby_client._make_request(
                "/candidate.search",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Search results: {json.dumps(response, indent=2)}")]
            
        elif name == "list_candidates":
            response = ashby_client._make_request(
                "/candidate.list",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Candidate list: {json.dumps(response, indent=2)}")]
            
        elif name == "create_job":
            response = ashby_client._make_request(
                "/job.create",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Created job: {json.dumps(response, indent=2)}")]
            
        elif name == "search_jobs":
            response = ashby_client._make_request(
                "/job.search",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Job search results: {json.dumps(response, indent=2)}")]
            
        elif name == "create_application":
            response = ashby_client._make_request(
                "/application.create",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Created application: {json.dumps(response, indent=2)}")]
            
        elif name == "list_applications":
            response = ashby_client._make_request(
                "/application.list",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Application list: {json.dumps(response, indent=2)}")]
            
        elif name == "create_interview":
            response = ashby_client._make_request(
                "/interview.create",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Created interview: {json.dumps(response, indent=2)}")]
            
        elif name == "list_interviews":
            response = ashby_client._make_request(
                "/interview.list",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Interview list: {json.dumps(response, indent=2)}")]
            
        elif name == "list_feedback":
            response = ashby_client._make_request(
                "/applicationFeedback.list",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Feedback list: {json.dumps(response, indent=2)}")]

        elif name == "submit_feedback":
            response = ashby_client._make_request(
                "/applicationFeedback.submit",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Submitted feedback: {json.dumps(response, indent=2)}")]

        elif name == "list_feedback_forms":
            response = ashby_client._make_request(
                "/feedbackFormDefinition.list",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Feedback forms: {json.dumps(response, indent=2)}")]

        elif name == "get_feedback_form":
            response = ashby_client._make_request(
                "/feedbackFormDefinition.info",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Feedback form: {json.dumps(response, indent=2)}")]

        elif name == "list_candidate_notes":
            response = ashby_client._make_request(
                "/candidate.listNotes",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Candidate notes: {json.dumps(response, indent=2)}")]

        elif name == "get_pipeline_metrics":
            response = ashby_client._make_request(
                "/analytics.pipeline",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Pipeline metrics: {json.dumps(response, indent=2)}")]
            
        elif name == "bulk_create_candidates":
            response = ashby_client._make_request(
                "/candidate.bulkCreate",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Bulk create results: {json.dumps(response, indent=2)}")]
            
        elif name == "bulk_update_applications":
            response = ashby_client._make_request(
                "/application.bulkUpdate",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Bulk update results: {json.dumps(response, indent=2)}")]
            
        elif name == "bulk_schedule_interviews":
            response = ashby_client._make_request(
                "/interview.bulkSchedule",
                method="POST",
                data=arguments
            )
            return [types.TextContent(type="text", text=f"Bulk schedule results: {json.dumps(response, indent=2)}")]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.exception("Error executing tool %s", name)
        return [types.TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

async def run():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ashby-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(run()) 