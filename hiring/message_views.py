# message_views.py - FIXED VERSION
import json
import os
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count, Max, Prefetch, OuterRef, Subquery
from django.utils import timezone
from django.core.files.storage import default_storage
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
import logging
import uuid
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

from .models import *
from .serializers import *
# ==================== HELPER FUNCTIONS ====================

# Conversation ViewSet
# message_views.py - FIXED ConversationViewSet
class ConversationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        try:
            # Simple query without any complex filters
            conversations = Conversation.objects.filter(
                participants=request.user
            ).order_by('-updated_at')
            
            serializer = ConversationSerializer(conversations, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'conversations': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error loading conversations: {str(e)}")
            return Response({
                'success': False,
                'error': 'Error loading conversations',
                'conversations': []
            })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread message count for current user"""
        try:
            unread_count = Message.objects.filter(
                conversation__participants=request.user,
                is_read=False
            ).exclude(sender=request.user).count()
            
            return Response({
                'success': True,
                'unread_count': unread_count
            })
        except Exception as e:
            logger.error(f"Error getting unread count: {str(e)}")
            return Response({
                'success': True,
                'unread_count': 0
            })

    # ADD THIS MISSING METHOD
    @action(detail=False, methods=['post'], url_path='start/(?P<user_id>[^/.]+)')
    def start_conversation(self, request, user_id=None):
        """Start a new conversation with a user"""
        try:
            # Get the target user
            target_user = get_object_or_404(CustomUser, id=user_id)
            
            # Don't allow starting conversation with yourself
            if target_user.id == request.user.id:
                return Response({
                    'success': False,
                    'error': 'Cannot start conversation with yourself'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if conversation already exists between these users
            existing_conversation = Conversation.objects.filter(
                participants=request.user
            ).filter(
                participants=target_user
            ).distinct().first()
            
            if existing_conversation:
                # Return existing conversation
                serializer = ConversationSerializer(existing_conversation, context={'request': request})
                return Response({
                    'success': True,
                    'conversation': serializer.data,
                    'message': 'Conversation already exists'
                })
            
            # Create new conversation
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, target_user)
            conversation.save()
            
            serializer = ConversationSerializer(conversation, context={'request': request})
            return Response({
                'success': True,
                'conversation': serializer.data,
                'message': 'Conversation started successfully'
            })
            
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error starting conversation: {str(e)}")
            return Response({
                'success': False,
                'error': 'Error starting conversation'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            
# Message ViewSet
class MessageViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request, conversation_id=None):
        try:
            # Verify user has access to this conversation
            conversation = Conversation.objects.filter(
                id=conversation_id,
                participants=request.user
            ).first()
            
            if not conversation:
                return Response({
                    'success': False,
                    'error': 'Conversation not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            messages = Message.objects.filter(
                conversation_id=conversation_id,
                conversation__participants=request.user
            ).select_related('sender', 'parent_message', 'original_sender').order_by('created_at')
            
            serializer = MessageSerializer(messages, many=True, context={'request': request})
            
            # Mark messages as read
            Message.objects.filter(
                conversation=conversation,
                is_read=False
            ).exclude(sender=request.user).update(
                is_read=True,
                read_at=timezone.now()
            )
            
            conversation_data = ConversationSerializer(conversation, context={'request': request}).data
            
            return Response({
                'success': True,
                'conversation': conversation_data,
                'messages': serializer.data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, conversation_id=None):
        try:
            conversation = Conversation.objects.filter(
                id=conversation_id,
                participants=request.user
            ).first()
            
            if not conversation:
                return Response({
                    'success': False,
                    'error': 'Conversation not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = MessageCreateSerializer(data=request.data)
            if serializer.is_valid():
                message = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    **serializer.validated_data
                )
                
                # Update conversation timestamp
                conversation.save()
                
                message_data = MessageSerializer(message, context={'request': request}).data
                return Response({
                    'success': True,
                    'message': message_data
                })
            
            return Response({
                'success': False,
                'error': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='send-file')
    def send_file(self, request, conversation_id=None):
        try:
            conversation = Conversation.objects.filter(
                id=conversation_id,
                participants=request.user
            ).first()
            
            if not conversation:
                return Response({
                    'success': False,
                    'error': 'Conversation not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = FileUploadSerializer(data=request.data)
            if serializer.is_valid():
                file = serializer.validated_data['file']
                message_type = serializer.validated_data['message_type']
                
                # Determine message type from file if not specified
                if message_type == 'file':
                    import mimetypes
                    mime_type, _ = mimetypes.guess_type(file.name)
                    if mime_type:
                        if mime_type.startswith('image/'):
                            message_type = 'image'
                        elif mime_type.startswith('video/'):
                            message_type = 'video'
                        elif mime_type.startswith('audio/'):
                            message_type = 'audio'
                
                message = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    message_type=message_type,
                    file=file,
                    file_name=file.name,
                    file_size=file.size,
                    file_mime_type=file.content_type
                )
                
                # Update conversation timestamp
                conversation.save()
                
                message_data = MessageSerializer(message, context={'request': request}).data
                return Response({
                    'success': True,
                    'message': message_data
                })
            
            return Response({
                'success': False,
                'error': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def reply(self, request, conversation_id=None, pk=None):
        try:
            parent_message = Message.objects.get(
                id=pk,
                conversation_id=conversation_id,
                conversation__participants=request.user
            )
            conversation = parent_message.conversation
            
            serializer = MessageCreateSerializer(data=request.data)
            if serializer.is_valid():
                message = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    parent_message=parent_message,
                    **serializer.validated_data
                )
                
                conversation.save()
                
                message_data = MessageSerializer(message, context={'request': request}).data
                return Response({
                    'success': True,
                    'message': message_data
                })
            
            return Response({
                'success': False,
                'error': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Message.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Message not found'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def forward(self, request, conversation_id=None, pk=None):
        try:
            original_message = Message.objects.get(
                id=pk,
                conversation_id=conversation_id,
                conversation__participants=request.user
            )
            target_conversation_id = request.data.get('target_conversation_id')
            
            if not target_conversation_id:
                return Response({
                    'success': False,
                    'error': 'Target conversation ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            target_conversation = Conversation.objects.filter(
                id=target_conversation_id,
                participants=request.user
            ).first()
            
            if not target_conversation:
                return Response({
                    'success': False,
                    'error': 'Target conversation not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Create forwarded message
            message = Message.objects.create(
                conversation=target_conversation,
                sender=request.user,
                content=original_message.content,
                message_type=original_message.message_type,
                file=original_message.file,
                file_name=original_message.file_name,
                file_size=original_message.file_size,
                file_mime_type=original_message.file_mime_type,
                is_forwarded=True,
                original_sender=original_message.sender
            )
            
            target_conversation.save()
            
            message_data = MessageSerializer(message, context={'request': request}).data
            return Response({
                'success': True,
                'message': message_data
            })
            
        except Message.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Message not found'
            }, status=status.HTTP_404_NOT_FOUND)

# User ViewSet - FIXED: Use UserSerializer instead of CustomUserSerializer
# In your message_views.py - Update the UserViewSet

class UserViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        try:
            # Exclude current user and return other users
            users = CustomUser.objects.exclude(id=request.user.id)
            
            # Add basic user data to check if it's working
            user_data = []
            for user in users:
                user_data.append({
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                    'email': user.email,
                    'is_online': getattr(user, 'is_online', False)  # Fallback if no status
                })
            
            return Response({
                'success': True,
                'users': user_data
            })
            
        except Exception as e:
            logger.error(f"Error loading users: {str(e)}")
            return Response({
                'success': False,
                'error': 'Error loading users',
                'users': []
            })

    @action(detail=False, methods=['get'])
    def search(self, request):
        try:
            query = request.GET.get('q', '').strip()
            
            if not query:
                return Response({
                    'success': True,
                    'users': []
                })
            
            users = CustomUser.objects.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query)
            ).exclude(id=request.user.id)
            
            user_data = []
            for user in users:
                user_data.append({
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                    'email': user.email,
                    'is_online': getattr(user, 'is_online', False)
                })
            
            return Response({
                'success': True,
                'users': user_data
            })
            
        except Exception as e:
            logger.error(f"Error searching users: {str(e)}")
            return Response({
                'success': False,
                'error': 'Error searching users',
                'users': []
            })

    @action(detail=False, methods=['get'])
    def available(self, request):
        try:
            users = CustomUser.objects.exclude(id=request.user.id)
            
            user_data = []
            for user in users:
                user_data.append({
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                    'email': user.email,
                    'is_online': getattr(user, 'is_online', False)
                })
            
            return Response({
                'success': True,
                'users': user_data
            })
            
        except Exception as e:
            logger.error(f"Error loading available users: {str(e)}")
            return Response({
                'success': False,
                'error': 'Error loading available users',
                'users': []
            })
        

class UserStatusViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def set_online(self, request):
        try:
            status_obj, created = UserStatus.objects.get_or_create(user=request.user)
            status_obj.is_online = True
            status_obj.last_seen = timezone.now()
            status_obj.save()
            
            return Response({
                'success': True,
                'message': 'Status updated to online'
            })
        except Exception as e:
            logger.error(f"Error setting online status: {str(e)}")
            return Response({
                'success': False,
                'error': 'Error updating status'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def set_offline(self, request):
        try:
            status_obj, created = UserStatus.objects.get_or_create(user=request.user)
            status_obj.is_online = False
            status_obj.last_seen = timezone.now()
            status_obj.save()
            
            return Response({
                'success': True,
                'message': 'Status updated to offline'
            })
        except Exception as e:
            logger.error(f"Error setting offline status: {str(e)}")
            return Response({
                'success': False,
                'error': 'Error updating status'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def typing(self, request):
        try:
            conversation_id = request.data.get('conversation_id')
            is_typing = request.data.get('is_typing', False)
            
            status_obj, created = UserStatus.objects.get_or_create(user=request.user)
            
            if is_typing and conversation_id:
                try:
                    conversation = Conversation.objects.get(id=conversation_id, participants=request.user)
                    status_obj.typing_to = conversation
                except Conversation.DoesNotExist:
                    pass
            else:
                status_obj.typing_to = None
                
            status_obj.save()
            
            return Response({
                'success': True,
                'message': 'Typing status updated'
            })
        except Exception as e:
            logger.error(f"Error updating typing status: {str(e)}")
            return Response({
                'success': False,
                'error': 'Error updating typing status'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def send_file_message(request, conversation_id):
    """Enhanced file upload endpoint with better media handling"""
    try:
        # Verify conversation access
        conversation = Conversation.objects.filter(
            id=conversation_id,
            participants=request.user
        ).first()
        
        if not conversation:
            return Response({
                'success': False,
                'error': 'Conversation not found'
            }, status=404)
        
        # Get uploaded file
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({
                'success': False,
                'error': 'No file provided'
            }, status=400)
        
        # Check file size (100MB limit)
        if uploaded_file.size > 504857600:  # 100MB
            return Response({
                'success': False,
                'error': 'File size exceeds 100MB limit'
            }, status=400)
        
        # Determine message type based on file content
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        mime_type = uploaded_file.content_type
        
        # Map file types
        message_type = 'file'  # default
        
        if mime_type.startswith('image/'):
            message_type = 'image'
        elif mime_type.startswith('video/'):
            message_type = 'video'
        elif mime_type.startswith('audio/'):
            message_type = 'audio'
        elif file_extension in ['.pdf', '.doc', '.docx', '.txt', '.rtf']:
            message_type = 'document'
        
        # Generate unique filename to avoid conflicts
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Save file with unique name
        file_path = default_storage.save(f'message_files/{unique_filename}', ContentFile(uploaded_file.read()))
        
        # Create message
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            message_type=message_type,
            file=file_path,  # This should be the path to the file
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            file_mime_type=uploaded_file.content_type
        )
        
        # Update conversation timestamp
        conversation.updated_at = timezone.now()
        conversation.save()
        
        # Get the full URL for the file
        file_url = request.build_absolute_uri(default_storage.url(file_path))
        
        serializer = MessageSerializer(message, context={'request': request})
        return Response({
            'success': True,
            'message': serializer.data,
            'file_url': file_url  # Include the full file URL
        })
        
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        return Response({
            'success': False,
            'error': f'File upload failed: {str(e)}'
        }, status=500)
    
# Function-based views for simple endpoints
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_user_status(request):
    status_obj, created = UserStatus.objects.get_or_create(user=request.user)
    status_obj.last_seen = timezone.now()
    status_obj.save()
    
    return JsonResponse({'success': True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_status(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        status_obj = UserStatus.objects.get(user=user)
        serializer = UserStatusSerializer(status_obj, context={'request': request})
        return Response({
            'success': True,
            'status': serializer.data
        })
    except (CustomUser.DoesNotExist, UserStatus.DoesNotExist):
        return Response({
            'success': False,
            'error': 'User status not found'
        }, status=status.HTTP_404_NOT_FOUND)