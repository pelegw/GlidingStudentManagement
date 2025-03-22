# training_records/management/commands/import_initial_data.py
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from training_records.models import TrainingTopic, Exercise

class Command(BaseCommand):
    help = 'Import training topics and exercises from Excel files if the database is empty'
    
    def handle(self, *args, **options):
        # Import required libraries
        try:
            import pandas as pd
        except ImportError:
            self.stdout.write(self.style.ERROR("This command requires pandas. Please install it with: pip install pandas"))
            return
            
        # Define paths to the Excel files
        base_dir = settings.BASE_DIR
        topics_excel = os.path.join(base_dir, 'data', 'training_topics.xlsx')
        exercises_excel = os.path.join(base_dir, 'data', 'exercises.xlsx')
        
        # Check if files exist
        if not os.path.exists(topics_excel):
            self.stdout.write(self.style.WARNING(f'Topics Excel file not found at {topics_excel}'))
            return
            
        if not os.path.exists(exercises_excel):
            self.stdout.write(self.style.WARNING(f'Exercises Excel file not found at {exercises_excel}'))
            return
        
        # Check if database is already populated
        if TrainingTopic.objects.exists() or Exercise.objects.exists():
            self.stdout.write(self.style.WARNING('Database already contains data. Skipping import.'))
            return
        
        # Import training topics
        try:
            df_topics = pd.read_excel(topics_excel)
            topics_count = 0
            
            for _, row in df_topics.iterrows():
                # Handle NaN values that pandas might introduce
                TrainingTopic.objects.create(
                    name=row['name'] if not pd.isna(row['name']) else '',
                    description=row['description'] if not pd.isna(row['description']) else '',
                    category=row['category'] if not pd.isna(row['category']) else '',
                    required_for_certification=str(row.get('required_for_certification', '')).lower() == 'true'
                )
                topics_count += 1
                
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {topics_count} training topics'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing training topics: {str(e)}'))
        
        # Import exercises
        try:
            df_exercises = pd.read_excel(exercises_excel)
            exercises_count = 0
            
            for _, row in df_exercises.iterrows():
                Exercise.objects.create(
                    name=row['name'] if not pd.isna(row['name']) else '',
                    description=row['description'] if not pd.isna(row['description']) else '',
                    category=row['category'] if not pd.isna(row['category']) else '',
                    number=row['number'] if not pd.isna(row['number']) else '',
                    is_required=str(row.get('is_required', '')).lower() == 'true'
                )
                exercises_count += 1
                
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {exercises_count} exercises'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing exercises: {str(e)}'))