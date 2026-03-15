# Task Generation Service

import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session  # Ensure correct import for type hint

from database.models.governance_task import GovernanceTask
from database.models.security_incident import SecurityIncident
from database.models.security_state import SecurityState
from database.database import SessionLocal as Session
from services.test_failure_task_service import TestFailureTaskService


class TaskGenerationService:
    """Service for generating governance tasks from various sources."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.test_failure_service = TestFailureTaskService(db=db_session)

    def create_task(
        self, 
        title: str, 
        description: str, 
        source_type: str, 
        source_id: Optional[int] = None,
        source_module: str = "manual", 
        priority: str = "medium", 
        company_id: int = None,
        incident_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GovernanceTask:
        """
        Create a new governance task.
        
        Args:
            title: Task title
            description: Detailed task description
            source_type: Type of source (e.g., 'manual', 'test_failure', 'security_incident')
            source_id: ID of the source entity
            source_module: Module that generated the task
            priority: Task priority ('low', 'medium', 'high')
            company_id: Associated company ID
            incident_id: Associated incident ID if applicable
            metadata: Additional metadata as JSON
            
        Returns:
            GovernanceTask: The created task
        """
        existing_task = self.db_session.query(GovernanceTask).filter_by(
            source_type=source_type, source_id=source_id, company_id=company_id, status="todo"
        ).first()

        if existing_task:
            # Prevent duplicate tasks for the same source
            return existing_task

        # Store metadata as JSON if provided
        metadata_json = None
        if metadata:
            try:
                metadata_json = json.dumps(metadata)
            except (TypeError, ValueError):
                # If metadata can't be serialized, log but don't fail
                pass

        new_task = GovernanceTask(
            title=title,
            description=description,
            source_type=source_type,
            source_id=str(source_id) if source_id else None,
            source_module=source_module,
            priority=priority,
            company_id=company_id,
            incident_id=incident_id,
            status="todo",
            metadata_json=metadata_json,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db_session.add(new_task)
        self.db_session.commit()
        return new_task

    def create_task_from_test_failure(
        self,
        test_name: str,
        test_file: str,
        failure_reason: str,
        company_id: int,
        priority: str = "medium",
        **additional_metadata
    ) -> GovernanceTask:
        """
        Create a task from a test failure with detailed error information.
        
        Args:
            test_name: Name of the failing test
            test_file: File path where the test is located
            failure_reason: Error message or reason for failure
            company_id: Associated company ID
            priority: Task priority
            **additional_metadata: Additional metadata to store with the task
            
        Returns:
            GovernanceTask: The created task
        """
        title = f"Fix failing test: {test_name}"
        description = f"Test: {test_name}\nFile: {test_file}\n\nFailure Reason:\n{failure_reason}"
        
        # Build source_id from test file and name
        source_id = f"{test_file}::{test_name}"
        
        # Prepare metadata
        metadata = {
            "test_name": test_name,
            "test_file": test_file,
            "failure_reason": failure_reason[:200],  # Store truncated version in metadata
            **additional_metadata
        }
        
        return self.create_task(
            title=title,
            description=description,
            source_type="test_failure",
            source_id=source_id,
            source_module="testing",
            priority=priority,
            company_id=company_id,
            metadata=metadata,
        )

    def create_task_from_security_incident(self, incident: SecurityIncident) -> GovernanceTask:
        """
        Create a task from a security incident.
        """
        title = f"Investigate Security Incident: {incident.id}"
        description = f"Severity: {incident.severity}\nDescription: {incident.description}"
        return self.create_task(
            title=title,
            description=description,
            source_type="security_incident",
            source_id=incident.id,
            source_module="security",
            priority="high" if incident.severity in ["high", "critical"] else "medium",
            company_id=incident.company_id,
            incident_id=incident.id
        )

    def create_task_from_security_state(self, state: SecurityState) -> GovernanceTask:
        """
        Create a task from a security state anomaly.
        """
        title = f"Review Security State: {state.state_key}"
        description = f"Namespace: {state.namespace}\nState Key: {state.state_key}\nCounter Value: {state.counter_value}"
        return self.create_task(
            title=title,
            description=description,
            source_type="security_state",
            source_id=state.id,
            source_module="security",
            priority="medium",
            company_id=state.company_id
        )

    def create_generic_task(self, task_data: Dict[str, Any]) -> GovernanceTask:
        """
        Create a generic governance task from raw data.
        
        Args:
            task_data: Dictionary containing task fields
            
        Returns:
            GovernanceTask: The created task
        """
        # Extract common fields
        title = task_data.get("title")
        description = task_data.get("description", "")
        company_id = task_data.get("company_id")
        
        if not title or not company_id:
            raise ValueError("Task must have at least 'title' and 'company_id'")
        
        # Create using the main create_task method to ensure consistency
        return self.create_task(
            title=title,
            description=description,
            source_type=task_data.get("source_type", "manual"),
            source_id=task_data.get("source_id"),
            source_module=task_data.get("source_module", "manual"),
            priority=task_data.get("priority", "medium"),
            company_id=company_id,
            incident_id=task_data.get("incident_id"),
            metadata=task_data.get("metadata"),
        )

# Example usage
# db_session = Session()
# task_service = TaskGenerationService(db_session)
# task_service.create_task("Example Task", "This is a test task", "manual", company_id=1)