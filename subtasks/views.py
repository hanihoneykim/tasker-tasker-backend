from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
)
from rest_framework.exceptions import NotFound, PermissionDenied
from .models import SubTask
from teams.models import Team
from .serializers import SubTaskSerializer


class SubTasks(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        subtasks = SubTask.objects.all()
        serializer = SubTaskSerializer(
            subtasks,
            context={"request": request},
            many=True,
        )
        return Response(serializer.data, status=HTTP_200_OK)


class SubTaskDetail(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, pk):
        try:
            return SubTask.objects.get(pk=pk)
        except SubTask.DoesNotExist:
            raise NotFound

    def get(self, request, pk):
        subtask = self.get_object(pk)
        serializer = SubTaskSerializer(
            subtask,
            context={"request": request},
        )
        return Response(serializer.data)

    def put(self, request, pk):
        subtask = self.get_object(pk)
        user = request.user

        # 팀에 속한 멤버인지 확인
        team_members = subtask.team.all().values_list("members", flat=True)
        if user.id not in team_members:
            raise PermissionDenied("You do not have permission to edit this SubTask.")

        serializer = SubTaskSerializer(
            subtask,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if serializer.is_valid():
            # is_complete가 True로 설정된 경우 completed_date를 현재 시간으로 업데이트
            if request.data.get("is_complete") is True:
                subtask.is_complete = True
                subtask.completed_date = timezone.now()

            # team을 string으로 받았다면 해당 처리
            if "team" in request.data:
                team_names_str = request.data["team"]
                team_names = [team_name.strip() for team_name in team_names_str.split(",")]
                subtask.team.clear()
                for team_name in team_names:
                    try:
                        team = Team.objects.get(name=team_name)
                        subtask.team.add(team)
                    except Team.DoesNotExist:
                        pass

            subtask.save()

            # task의 모든 SubTask가 완료되면 Task의 is_complete도 True로 설정
            task = subtask.task
            all_subtasks_complete = (
                task.subtasks.all().filter(is_complete=True).count() == task.subtasks.all().count()
            )
            if all_subtasks_complete:
                task.is_complete = True
                task.save()

            serializer = SubTaskSerializer(subtask)
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        subtask = self.get_object(pk)
        if request.user not in subtask.team.all().members.all():
            raise PermissionDenied
        if subtask.is_complete:
            return Response({"주의": "완료된 하위과제는 삭제할 수 없습니다."}, status=HTTP_400_BAD_REQUEST)
        subtask.delete()
        return Response(status=HTTP_204_NO_CONTENT)
