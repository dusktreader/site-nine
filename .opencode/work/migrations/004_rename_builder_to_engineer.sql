-- Migration: Rename Builder role to Engineer
-- Created: 2026-02-04
-- Purpose: Update all Builder references to Engineer throughout the database
--          and rename BLD task prefix to ENG

-- Update personas table
UPDATE personas SET role = 'Engineer' WHERE role = 'Builder';

-- Update missions table
UPDATE missions SET role = 'Engineer' WHERE role = 'Builder';

-- Update handoffs table (to_role)
UPDATE handoffs SET to_role = 'Engineer' WHERE to_role = 'Builder';

-- Update tasks table (role and task IDs)
UPDATE tasks SET role = 'Engineer' WHERE role = 'Builder';
UPDATE tasks SET id = 'ENG-' || substr(id, 5) WHERE id LIKE 'BLD-%';
UPDATE tasks SET file_path = replace(file_path, '/BLD-', '/ENG-') WHERE file_path LIKE '%/BLD-%';

-- Update task_templates table
UPDATE task_templates SET role = 'Engineer' WHERE role = 'Builder';

-- Update task dependencies
UPDATE task_dependencies SET task_id = 'ENG-' || substr(task_id, 5) WHERE task_id LIKE 'BLD-%';
UPDATE task_dependencies SET depends_on_task_id = 'ENG-' || substr(depends_on_task_id, 5) WHERE depends_on_task_id LIKE 'BLD-%';

-- Update epics table (if any tasks reference BLD)
-- Note: Epic task references are in the file_path, handled by file renames

