from django.core.management.base import BaseCommand
from user.models import ChatbotKnowledge

class Command(BaseCommand):
    help = 'Populates the chatbot knowledge base with initial data'

    def handle(self, *args, **kwargs):
        knowledge_base = [
            {
                'topic': 'Courses',
                'question': 'What courses do you offer?',
                'answer': 'We offer a variety of courses across different categories including development programs. You can browse all available courses in the Courses section.',
                'category': 'general'
            },
            {
                'topic': 'Enrollment',
                'question': 'How do I enroll in a course?',
                'answer': 'To enroll in a course: 1. Browse available courses 2. Select your desired course 3. Click "Enroll Now" 4. For paid courses, complete the payment process 5. Start learning!',
                'category': 'enrollment'
            },
            # Add more knowledge base entries here
        ]

        for item in knowledge_base:
            ChatbotKnowledge.objects.get_or_create(
                topic=item['topic'],
                question=item['question'],
                answer=item['answer'],
                category=item['category']
            )

        self.stdout.write(self.style.SUCCESS('Successfully populated chatbot knowledge base')) 