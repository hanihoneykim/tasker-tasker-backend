from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)
from rest_framework.exceptions import NotFound, PermissionDenied
from .models import Task
from teams.models import Team
from subtasks.models import SubTask
from subtasks.serializers import SubTaskSerializer, TinySubTaskSerializer
from .serializers import TaskSerializer


class Tasks(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        tasks = Task.objects.all()
        serializer = TaskSerializer(
            tasks,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=HTTP_200_OK)

    def post(self, request):
        task_serializer = TaskSerializer(data=request.data)
        if task_serializer.is_valid():
            task = task_serializer.save(create_user=request.user)
            team_name = request.data.get("team")
            try:
                team = Team.objects.get(name=team_name)
                task.team = team
                task.save()
            except Team.DoesNotExist:
                return Response(
                    {"error": f"팀 '{team_name}'을(를) 찾을 수 없음"}, status=HTTP_400_BAD_REQUEST
                )
            subtasks = SubTask.objects.filter(task=task)
            subtask_serializer = SubTaskSerializer(subtasks, many=True)
            return Response(
                {
                    "task": task_serializer.data,
                    "subtasks": subtask_serializer.data,
                },
                status=HTTP_201_CREATED,
            )
        else:
            return Response(task_serializer.errors, status=HTTP_400_BAD_REQUEST)


class TaskDetail(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, pk):
        try:
            return Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            raise NotFound

    def get(self, request, pk):
        task = self.get_object(pk)
        serializer = TaskSerializer(
            task,
            context={"request": request},
        )
        return Response(serializer.data)

    def put(self, request, pk):
        task = self.get_object(pk)
        # 작성자만 수정 가능
        if task.create_user != request.user:
            raise PermissionDenied

        serializer = TaskSerializer(
            task,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        if serializer.is_valid():
            # 주 작업의 팀을 업데이트하려면
            new_team = serializer.validated_data.get("team")
            if new_team:
                task.team = new_team
                task.save()

            # 서브태스크 처리
            subtask_data = request.data.get("subtasks", [])
            if subtask_data:
                for subtask_info in subtask_data:
                    # is_coplete 처리
                    is_complete = subtask_info.get("is_complete")
                    if is_complete:
                        continue

                    # subtask-team 처리
                    subtask_id = subtask_info.get("id")
                    subtask = task.subtasks.get(id=subtask_id)
                    subtask.team.clear()  # 기존 팀 정보 초기화

                    if "team" in subtask_info:
                        team_names_str = subtask_info["team"]
                        team_names = [team_name.strip() for team_name in team_names_str.split(",")]
                        for team_name in team_names:
                            try:
                                team = Team.objects.get(name=team_name)
                                subtask.team.add(team)
                            except Team.DoesNotExist:
                                pass

            task.save()
            serializer = TaskSerializer(task)
            return Response(serializer.data)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class TaskSubTasks(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, pk):
        try:
            return Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            raise NotFound

    def get(self, request, pk):
        task = self.get_object(pk)
        subtasks = SubTask.objects.filter(task=task)  # 해당 task에 속하는 모든 subtasks 가져오기
        serializer = SubTaskSerializer(
            subtasks,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

    def post(self, request, pk):
        task = self.get_object(pk)
        # request 데이터에서 "team" 필드의 문자열 리스트를 추출
        team_names = request.data.get("team", [])
        subtask = SubTask.objects.create(task=task)

        for team_name in team_names:
            try:
                team = Team.objects.get(name=team_name)
                subtask.team.add(team)
            except Team.DoesNotExist:
                return Response(
                    {"error": f"팀 '{team_name}'을(를) 찾을 수 없음"}, status=HTTP_404_NOT_FOUND
                )
        serializer = SubTaskSerializer(subtask, context={"request": request})
        return Response(serializer.data, status=HTTP_201_CREATED)
