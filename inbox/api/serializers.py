from notifications.models import Notification
from rest_framework import serializers


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = (
            'id',
            'actor_content_type',
            'actor_object_id',
            'verb',
            'action_object_content_type',
            'action_object_object_id',
            'target_content_type',
            'target_object_id',
            'timestamp',
            'unread',
        )
        # TODO [Homework] 将 content_type/object_id 转换为具体对象信息


class NotificationSerializerForUpdate(serializers.ModelSerializer):
    unread = serializers.BooleanField()

    class Meta:
        model = Notification
        fields = ('unread',)    # 明确可更新字段白名单

    def update(self, instance, validated_data):
        instance.unread = validated_data.get('unread')
        instance.save()
        return instance