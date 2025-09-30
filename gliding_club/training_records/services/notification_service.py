import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

# Get the User model
User = get_user_model()

logger = logging.getLogger(__name__)

class NotificationService:
    
    @staticmethod
    def notify_student_revision_needed(training_record):
        """Send immediate email to student when instructor saves without signing off"""
        
        # Import inside function to avoid circular imports
        from django.apps import apps
        PendingNotification = apps.get_model('training_records', 'PendingNotification')
        
        logger.info(f'Attempting to send revision needed notification for record {training_record.pk} to student {training_record.student.email}')
        
        # Create or update notification record
        try:
            notification, created = PendingNotification.objects.get_or_create(
                user=training_record.student,
                notification_type='student_revision_needed',
                training_record=training_record,
                defaults={'created_at': timezone.now()}
            )
        except Exception as e:
            logger.error(f'Failed to create notification record for training record {training_record.pk}: {e}')
            return False, "Failed to create notification record"
        
        # Skip if already sent
        if notification.is_sent:
            logger.info(f'Notification already sent for record {training_record.pk}')
            return True, "Notification already sent"
        
        # Check if student has email
        if not training_record.student.email or training_record.student.email.strip() == '':
            logger.warning(f'Skipping notification for record {training_record.pk} - student has no email address')
            return False, "Student has no email address"
        
        try:
            # Prepare email content
            subject = f"Training Record #{training_record.pk} - Instructor Comments Added"
            
            html_message = render_to_string('training_records/emails/revision_needed.html', {
                'student': training_record.student,
                'record': training_record,
                'instructor': training_record.instructor,
            })
            
            plain_message = render_to_string('training_records/emails/revision_needed.txt', {
                'student': training_record.student,
                'record': training_record,
                'instructor': training_record.instructor,
            })
            
            # Send email with error handling
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[training_record.student.email],
                fail_silently=False,
            )
            
            # Mark as sent
            notification.sent_at = timezone.now()
            notification.is_sent = True
            notification.save()
            
            logger.info(f'Successfully sent revision needed notification for record {training_record.pk}')
            return True, "Email sent successfully"
            
        except Exception as e:
            logger.error(f'Failed to send revision notification for record {training_record.pk}: {e}', exc_info=True)
            
            # Determine error type for better user messaging
            error_msg = str(e).lower()
            if 'access' in error_msg or 'permission' in error_msg or 'credential' in error_msg:
                return False, "Email service configuration issue"
            elif 'timeout' in error_msg or 'connection' in error_msg:
                return False, "Email service temporarily unavailable"
            elif 'invalid' in error_msg and 'email' in error_msg:
                return False, "Invalid email address"
            else:
                return False, "Email service error"
    
    @staticmethod
    def send_weekly_instructor_digest():
        """Send weekly digest to instructors with pending records"""
        
        # Import inside function to avoid circular imports
        from django.apps import apps
        TrainingRecord = apps.get_model('training_records', 'TrainingRecord')
        
        logger.info('Starting weekly instructor digest job')
        
        # Get all active instructors
        instructors = User.objects.filter(user_type='instructor', is_active=True)
        sent_count = 0
        error_count = 0
        skipped_count = 0
        
        for instructor in instructors:
            # Skip instructors without email addresses
            if not instructor.email or instructor.email.strip() == '':
                logger.warning(f'Skipping instructor {instructor.get_full_name()} (ID: {instructor.id}) - no email address')
                skipped_count += 1
                continue
                
            # Get unsigned records assigned to this instructor
            pending_records = TrainingRecord.objects.filter(
                instructor=instructor,
                signed_off=False
            ).order_by('-date')
            
            if pending_records.exists():
                logger.info(f'Sending weekly digest to {instructor.email} - {pending_records.count()} pending records')
                
                try:
                    subject = f"Weekly Digest - {pending_records.count()} Records Awaiting Sign-Off"
                    
                    html_message = render_to_string('training_records/emails/weekly_digest.html', {
                        'instructor': instructor,
                        'pending_records': pending_records,
                        'count': pending_records.count(),
                        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
                    })
                    
                    plain_message = render_to_string('training_records/emails/weekly_digest.txt', {
                        'instructor': instructor,
                        'pending_records': pending_records,
                        'count': pending_records.count(),
                        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
                    })
                    
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[instructor.email],
                        fail_silently=False,
                    )
                    
                    sent_count += 1
                    logger.info(f'Successfully sent weekly digest to {instructor.email}')
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f'Failed to send weekly digest to {instructor.email}: {e}', exc_info=True)
            else:
                logger.debug(f'No pending records for instructor {instructor.email}')
        
        logger.info(f'Weekly digest job completed. Sent: {sent_count}, Errors: {error_count}, Skipped: {skipped_count}')
        
        return {
            'sent_count': sent_count,
            'error_count': error_count,
            'skipped_count': skipped_count,
            'total_instructors': instructors.count()
        }