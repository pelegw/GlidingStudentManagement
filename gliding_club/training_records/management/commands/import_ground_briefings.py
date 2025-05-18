from django.core.management.base import BaseCommand
import pandas as pd
from training_records.models import GroundBriefingTopic
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Import ground briefing topics from Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Path to the Excel file')

    def handle(self, *args, **options):
        filepath = options['file']
        
        if not os.path.isabs(filepath):
            filepath = os.path.join(settings.BASE_DIR, filepath)
            
        if not os.path.exists(filepath):
            self.stderr.write(self.style.ERROR(f'File does not exist: {filepath}'))
            return
            
        try:
            # Read the Excel file
            df = pd.read_excel(filepath)
            
            # Check for required columns
            required_columns = ['number', 'name', 'details']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                self.stderr.write(self.style.ERROR(
                    f'Missing required columns: {", ".join(missing_columns)}'
                ))
                return
                
            # Import the data
            topics_created = 0
            topics_updated = 0
            
            for _, row in df.iterrows():
                number = int(row['number'])
                name = row['name']
                details = row['details'] if pd.notna(row['details']) else ""
                
                topic, created = GroundBriefingTopic.objects.update_or_create(
                    number=number,
                    defaults={
                        'name': name,
                        'details': details
                    }
                )
                
                if created:
                    topics_created += 1
                else:
                    topics_updated += 1
                    
            self.stdout.write(self.style.SUCCESS(
                f'Successfully imported {topics_created} new topics and updated {topics_updated} existing topics.'
            ))
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error importing data: {str(e)}'))