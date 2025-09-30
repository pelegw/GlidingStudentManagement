from django.core.management.base import BaseCommand
from training_records.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send weekly digest emails to instructors with pending records'

    def handle(self, *args, **options):
        self.stdout.write('Sending weekly instructor digests...')
        logger.info('Starting weekly instructor digest email job')
        
        try:
            result = NotificationService.send_weekly_instructor_digest()
            
            # Log results
            sent = result.get('sent_count', 0)
            errors = result.get('error_count', 0)
            skipped = result.get('skipped_count', 0)
            total = result.get('total_instructors', 0)
            
            if errors == 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully sent weekly digests to {sent} instructor(s). '
                        f'Skipped {skipped} instructor(s) without email addresses.'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Sent weekly digests to {sent} instructor(s) with {errors} error(s). '
                        f'Skipped {skipped} instructor(s) without email addresses. '
                        f'Check logs for details.'
                    )
                )
            
            logger.info(f'Weekly digest command completed. Sent: {sent}, Errors: {errors}, Skipped: {skipped}')
            
        except Exception as e:
            error_msg = f'Failed to send weekly digests: {e}'
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg, exc_info=True)