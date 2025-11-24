from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from likes.models import Like
from utils.decorators import required_params
from likes.api.serializers import (
    LikeSerializer,
    LikeSerializerForCreate,
)
class LikeViewSet(viewsets.GenericViewSet):
    queryset = Like.objects.all()
    serializer_class = LikeSerializerForCreate
    permission_classes = [IsAuthenticated]

    @required_params(request_attr='data', params=['content_type', 'object_id',])
    def create(self, request, *args, **kwargs):
        serializer = LikeSerializerForCreate(
            data=request.data,
            context={'request': request},
        )
        if not serializer.is_valid():
            return Response(data={
                'message': 'Please check input.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        like = serializer.save()
        return Response(
            data= LikeSerializer(instance=like).data,
            status=status.HTTP_201_CREATED
        )