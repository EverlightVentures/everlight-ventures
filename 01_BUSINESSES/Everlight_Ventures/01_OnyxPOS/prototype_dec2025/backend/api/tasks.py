"""
Task Management API (Asana-style)
- Create/update/delete tasks
- Assign tasks to users
- Track task status and progress
- Add comments and subtasks
- Organize tasks in projects
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Task, Project, TaskComment, User
from datetime import datetime

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("", methods=["GET"])
@jwt_required()
def list_tasks():
    """
    List tasks with filtering and sorting

    Query params:
    - status: Filter by status (to_do, in_progress, completed, blocked)
    - assigned_to: Filter by assigned user ID
    - project_id: Filter by project
    - priority: Filter by priority (low, medium, high, urgent)
    - due_before: ISO date - tasks due before this date
    - search: Search in title and description
    """
    try:
        tenant_id = g.tenant_id

        # Base query
        query = g.db.query(Task).filter_by(
            tenant_id=tenant_id,
            deleted_at=None
        )

        # Apply filters
        if request.args.get("status"):
            query = query.filter_by(status=request.args.get("status"))

        if request.args.get("assigned_to"):
            query = query.filter_by(assigned_to=request.args.get("assigned_to"))

        if request.args.get("project_id"):
            query = query.filter_by(project_id=request.args.get("project_id"))

        if request.args.get("priority"):
            query = query.filter_by(priority=request.args.get("priority"))

        if request.args.get("due_before"):
            due_before = datetime.fromisoformat(request.args.get("due_before"))
            query = query.filter(Task.due_date <= due_before)

        if request.args.get("search"):
            search_term = f"%{request.args.get('search')}%"
            query = query.filter(
                (Task.title.like(search_term)) |
                (Task.description.like(search_term))
            )

        # Exclude subtasks from main list (unless specifically requested)
        if not request.args.get("include_subtasks"):
            query = query.filter_by(parent_task_id=None)

        # Sort by due date (ascending), then priority
        query = query.order_by(
            Task.due_date.asc().nullslast(),
            Task.priority.desc()
        )

        # Pagination
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        tasks = query.limit(per_page).offset((page - 1) * per_page).all()

        return jsonify({
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                    "assigned_to": task.assigned_to,
                    "assignee_name": task.assignee.full_name if task.assignee else None,
                    "created_by": task.created_by,
                    "creator_name": task.creator.full_name if task.creator else None,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "start_date": task.start_date.isoformat() if task.start_date else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "project_id": task.project_id,
                    "parent_task_id": task.parent_task_id,
                    "tags": task.tags.split(",") if task.tags else [],
                    "subtask_count": len(task.subtasks),
                    "comment_count": len(task.comments),
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat()
                }
                for task in tasks
            ],
            "page": page,
            "per_page": per_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tasks_bp.route("", methods=["POST"])
@jwt_required()
def create_task():
    """Create a new task"""
    try:
        tenant_id = g.tenant_id
        user_id = get_jwt_identity()
        data = request.json

        # Validate required fields
        if not data.get("title"):
            return jsonify({"error": "Title is required"}), 400

        # Create task
        task = Task(
            tenant_id=tenant_id,
            title=data["title"],
            description=data.get("description"),
            status=data.get("status", "to_do"),
            priority=data.get("priority", "medium"),
            assigned_to=data.get("assigned_to"),
            created_by=user_id,
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            start_date=datetime.fromisoformat(data["start_date"]) if data.get("start_date") else None,
            project_id=data.get("project_id"),
            parent_task_id=data.get("parent_task_id"),
            tags=",".join(data.get("tags", [])) if data.get("tags") else None
        )

        g.db.add(task)
        g.db.commit()

        return jsonify({
            "message": "Task created successfully",
            "task": {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "assigned_to": task.assigned_to,
                "due_date": task.due_date.isoformat() if task.due_date else None
            }
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@tasks_bp.route("/<task_id>", methods=["GET"])
@jwt_required()
def get_task(task_id):
    """Get task details with subtasks and comments"""
    try:
        tenant_id = g.tenant_id

        task = g.db.query(Task).filter_by(
            id=task_id,
            tenant_id=tenant_id,
            deleted_at=None
        ).first()

        if not task:
            return jsonify({"error": "Task not found"}), 404

        return jsonify({
            "task": {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "assigned_to": task.assigned_to,
                "assignee": {
                    "id": task.assignee.id,
                    "name": task.assignee.full_name,
                    "email": task.assignee.email
                } if task.assignee else None,
                "created_by": task.created_by,
                "creator": {
                    "id": task.creator.id,
                    "name": task.creator.full_name,
                    "email": task.creator.email
                } if task.creator else None,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "start_date": task.start_date.isoformat() if task.start_date else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "project_id": task.project_id,
                "parent_task_id": task.parent_task_id,
                "tags": task.tags.split(",") if task.tags else [],
                "subtasks": [
                    {
                        "id": subtask.id,
                        "title": subtask.title,
                        "status": subtask.status,
                        "assigned_to": subtask.assigned_to,
                        "due_date": subtask.due_date.isoformat() if subtask.due_date else None
                    }
                    for subtask in task.subtasks
                ],
                "comments": [
                    {
                        "id": comment.id,
                        "content": comment.content,
                        "user_id": comment.user_id,
                        "user_name": comment.user.full_name,
                        "created_at": comment.created_at.isoformat()
                    }
                    for comment in task.comments
                ],
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tasks_bp.route("/<task_id>", methods=["PATCH"])
@jwt_required()
def update_task(task_id):
    """Update task"""
    try:
        tenant_id = g.tenant_id

        task = g.db.query(Task).filter_by(
            id=task_id,
            tenant_id=tenant_id,
            deleted_at=None
        ).first()

        if not task:
            return jsonify({"error": "Task not found"}), 404

        data = request.json

        # Update fields
        updatable_fields = [
            "title", "description", "status", "priority",
            "assigned_to", "project_id", "parent_task_id"
        ]

        for field in updatable_fields:
            if field in data:
                setattr(task, field, data[field])

        # Handle date fields
        if "due_date" in data:
            task.due_date = datetime.fromisoformat(data["due_date"]) if data["due_date"] else None

        if "start_date" in data:
            task.start_date = datetime.fromisoformat(data["start_date"]) if data["start_date"] else None

        if "tags" in data:
            task.tags = ",".join(data["tags"]) if data["tags"] else None

        # Auto-complete when status changes to completed
        if data.get("status") == "completed" and not task.completed_at:
            task.completed_at = datetime.utcnow()

        g.db.commit()

        return jsonify({
            "message": "Task updated successfully",
            "task": {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "updated_at": task.updated_at.isoformat()
            }
        }), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@tasks_bp.route("/<task_id>", methods=["DELETE"])
@jwt_required()
def delete_task(task_id):
    """Soft delete task"""
    try:
        tenant_id = g.tenant_id

        task = g.db.query(Task).filter_by(
            id=task_id,
            tenant_id=tenant_id,
            deleted_at=None
        ).first()

        if not task:
            return jsonify({"error": "Task not found"}), 404

        # Soft delete
        task.deleted_at = datetime.utcnow()
        g.db.commit()

        return jsonify({"message": "Task deleted successfully"}), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@tasks_bp.route("/<task_id>/comments", methods=["POST"])
@jwt_required()
def add_comment(task_id):
    """Add comment to task"""
    try:
        tenant_id = g.tenant_id
        user_id = get_jwt_identity()

        task = g.db.query(Task).filter_by(
            id=task_id,
            tenant_id=tenant_id,
            deleted_at=None
        ).first()

        if not task:
            return jsonify({"error": "Task not found"}), 404

        data = request.json
        if not data.get("content"):
            return jsonify({"error": "Content is required"}), 400

        comment = TaskComment(
            task_id=task_id,
            user_id=user_id,
            content=data["content"]
        )

        g.db.add(comment)
        g.db.commit()

        return jsonify({
            "message": "Comment added successfully",
            "comment": {
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


# ============= PROJECTS API =============

@tasks_bp.route("/projects", methods=["GET"])
@jwt_required()
def list_projects():
    """List all projects"""
    try:
        tenant_id = g.tenant_id

        projects = g.db.query(Project).filter_by(tenant_id=tenant_id).order_by(Project.name).all()

        return jsonify({
            "projects": [
                {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "color": project.color,
                    "status": project.status,
                    "owner_id": project.owner_id,
                    "task_count": len(project.tasks),
                    "completed_task_count": len([t for t in project.tasks if t.status == "completed"]),
                    "created_at": project.created_at.isoformat()
                }
                for project in projects
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tasks_bp.route("/projects", methods=["POST"])
@jwt_required()
def create_project():
    """Create new project"""
    try:
        tenant_id = g.tenant_id
        user_id = get_jwt_identity()
        data = request.json

        if not data.get("name"):
            return jsonify({"error": "Name is required"}), 400

        project = Project(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            color=data.get("color", "#3B82F6"),
            status=data.get("status", "active"),
            owner_id=user_id
        )

        g.db.add(project)
        g.db.commit()

        return jsonify({
            "message": "Project created successfully",
            "project": {
                "id": project.id,
                "name": project.name,
                "color": project.color
            }
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500
