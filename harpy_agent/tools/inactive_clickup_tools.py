# def create_clickup_subtask(parent_task_id: str, name: str, **kwargs) -> Dict[str, Any]:
#     """
#     Creates a new subtask under a specified parent task in ClickUp.
#     Accepts same optional args as create_clickup_task.

#     Args:
#         parent_task_id (str): The ID of the parent task under which the subtask will be created.
#         name (str): The name of the new subtask.
#         **kwargs: Additional optional arguments like description, assignees, status, priority, due_date, tags, custom_fields.

#     Returns:
#         Dict[str, Any]: A dictionary representing the newly created subtask. Raises an error if creation fails.
#     """
#     api = ClickUpAPI()
    
#     # Need the list_id of the parent task
#     try:
#         parent_task = get_clickup_task_details(parent_task_id)
#         list_id = parent_task.get("list", {}).get("id")
#         if not list_id:
#             raise ValueError(f"Could not find list_id for parent task {parent_task_id}")
#     except Exception as e:
#          raise ValueError(f"Failed to get parent task details to create subtask: {e}")

#     payload = {"name": name, "parent": parent_task_id} # Set parent field
    
#     # Add other optional args from kwargs if present
#     # (description, assignees, status, priority, due_date, tags, custom_fields_json)
#     if kwargs.get("description"): payload["description"] = kwargs["description"]
#     if kwargs.get("assignees"): payload["assignees"] = kwargs["assignees"]
#     if kwargs.get("status"): payload["status"] = kwargs["status"]
#     if kwargs.get("priority"): payload["priority"] = kwargs["priority"]
#     if kwargs.get("due_date"): payload["due_date"] = kwargs["due_date"]
#     if kwargs.get("tags"): payload["tags"] = kwargs["tags"]
    
#     # Handle custom fields similarly to create_clickup_task
#     if "custom_fields_json" in kwargs:
#         parsed_custom_fields = []
#         try:
#             for cf_str in kwargs["custom_fields_json"]:
#                  field_data = json.loads(cf_str)
#                  if "id" not in field_data or "value" not in field_data:
#                       raise ValueError(f"Subtask Custom field JSON missing 'id' or 'value': {cf_str}")
#                  parsed_custom_fields.append(field_data)
#             payload["custom_fields"] = parsed_custom_fields
#         except json.JSONDecodeError as e:
#             raise ValueError(f"Invalid JSON format in subtask custom_fields_json: {e}")
#         except ValueError as e:
#              raise e
             
#     try:
#         # Use the same endpoint as create_task, just include "parent" in payload
#         response = requests.post(
#             f"{api.base_url}/list/{list_id}/task", 
#             headers=api.headers, 
#             json=payload
#         )
#         response.raise_for_status()
#         return response.json()
#     except requests.exceptions.RequestException as e:
#         print(f"Error creating subtask under {parent_task_id} in list {list_id}: {e} - Response: {e.response.text if e.response else 'No response'}")
#         raise e
#     except json.JSONDecodeError:
#          print(f"Error decoding JSON response after creating subtask for {parent_task_id}.")
#          raise
