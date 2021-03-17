from dataclasses import dataclass

import graphene
from fastapi import FastAPI
from starlette.graphql import GraphQLApp


@dataclass
class TaskModel:
    idx: int
    description: str


class TaskManager:
    def __init__(self):
        self._running_idx = 0

        self._tasks_by_id = {}

    def _get_new_index(self):
        self._running_idx += 1
        return self._running_idx

    def get_task(self, idx: str) -> TaskModel:
        return self._tasks_by_id[idx]

    def get_all_tasks(self) -> list[TaskModel]:
        return list(self._tasks_by_id.values())

    def add_task(self, description: str) -> TaskModel:
        task = TaskModel(self._get_new_index(), description)
        self._tasks_by_id[str(task.idx)] = task
        return task

    def edit_task(self, idx: str, description: str) -> TaskModel:
        task = self.get_task(idx)
        task.description = description
        return task

    def delete_task(self, idx: str) -> TaskModel:
        task = self._tasks_by_id.pop(idx)
        return task


manager = TaskManager()


class Task(graphene.ObjectType):
    idx = graphene.ID()
    description = graphene.String()

    def resolve_idx(parent: TaskModel, info):
        return parent.idx

    def resolve_description(parent: TaskModel, info):
        return parent.description


class RootQuery(graphene.ObjectType):
    task = graphene.Field(Task, idx=graphene.ID(required=True))
    tasks = graphene.List(Task)

    def resolve_task(parent, info, idx):
        return manager.get_task(idx)

    def resolve_tasks(parent, info):
        return manager.get_all_tasks()


class AddTask(graphene.Mutation):
    class Arguments:
        description = graphene.String()

    ok = graphene.Boolean()
    task = graphene.Field(lambda: Task)

    def mutate(parent, info, description):
        task = manager.add_task(description)
        return AddTask(ok=True, task=task)


class EditTask(graphene.Mutation):
    class Arguments:
        idx = graphene.ID()
        description = graphene.String()

    ok = graphene.Boolean()
    task = graphene.Field(lambda: Task)

    def mutate(parent, info, idx, description):
        task = manager.edit_task(idx, description)
        return AddTask(ok=True, task=task)


class DeleteTask(graphene.Mutation):
    class Arguments:
        idx = graphene.ID()

    ok = graphene.Boolean()
    task = graphene.Field(lambda: Task)

    def mutate(parent, info, idx):
        task = manager.delete_task(idx)
        return AddTask(ok=True, task=task)


class RootMutation(graphene.ObjectType):
    add_task = AddTask.Field()
    edit_task = EditTask.Field()
    delete_task = DeleteTask.Field()


app = FastAPI()
app.add_route("/", GraphQLApp(schema=graphene.Schema(query=RootQuery, mutation=RootMutation)))

# Run:
# uvicorn main:app --reload
# Visit:
# http://127.0.0.1:8000/
