import os
import json
from datetime import datetime
from django.conf import settings

# Create metrics directory if it doesn't exist
METRICS_DIR = os.path.join(settings.MEDIA_ROOT, 'metrics')
os.makedirs(METRICS_DIR, exist_ok=True)

class MetricsTracker:
    @staticmethod
    def save_transcription_metrics(topic_id, audio_duration, word_count, estimated_accuracy):
        """Save transcription metrics to file"""
        timestamp = datetime.now().isoformat()
        metrics = {
            'timestamp': timestamp,
            'topic_id': topic_id,
            'audio_duration': audio_duration,
            'word_count': word_count,
            'estimated_accuracy': estimated_accuracy
        }
        
        metrics_file = os.path.join(METRICS_DIR, 'transcription_metrics.json')
        
        # Read existing metrics or create new list
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        else:
            data = []
        
        # Append new metrics and save
        data.append(metrics)
        with open(metrics_file, 'w') as f:
            json.dump(data, f)
        
        return metrics
    
    @staticmethod
    def save_translation_metrics(source_lang, target_lang, text_length, bleu_score):
        """Save translation quality metrics to file"""
        timestamp = datetime.now().isoformat()
        metrics = {
            'timestamp': timestamp,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'text_length': text_length,
            'bleu_score': bleu_score
        }
        
        metrics_file = os.path.join(METRICS_DIR, 'translation_metrics.json')
        
        # Read existing metrics or create new list
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        else:
            data = []
        
        # Append new metrics and save
        data.append(metrics)
        with open(metrics_file, 'w') as f:
            json.dump(data, f)
        
        return metrics
    
    @staticmethod
    def save_processing_metrics(operation_type, content_size, processing_time):
        """Save processing efficiency metrics to file"""
        timestamp = datetime.now().isoformat()
        metrics = {
            'timestamp': timestamp,
            'operation_type': operation_type,  # 'transcription' or 'translation'
            'content_size': content_size,
            'processing_time': processing_time,
            'efficiency': content_size / processing_time if processing_time > 0 else 0
        }
        
        metrics_file = os.path.join(METRICS_DIR, 'processing_metrics.json')
        
        # Read existing metrics or create new list
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        else:
            data = []
        
        # Append new metrics and save
        data.append(metrics)
        with open(metrics_file, 'w') as f:
            json.dump(data, f)
        
        return metrics

    @staticmethod
    def get_transcription_metrics():
        """Get transcription metrics data for charts"""
        metrics_file = os.path.join(METRICS_DIR, 'transcription_metrics.json')
        if not os.path.exists(metrics_file):
            return []
            
        with open(metrics_file, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
                
        return data
    
    @staticmethod
    def get_translation_metrics():
        """Get translation metrics data for charts"""
        metrics_file = os.path.join(METRICS_DIR, 'translation_metrics.json')
        if not os.path.exists(metrics_file):
            return []
            
        with open(metrics_file, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
                
        return data
    
    @staticmethod
    def get_processing_metrics():
        """Get processing metrics data for charts"""
        metrics_file = os.path.join(METRICS_DIR, 'processing_metrics.json')
        if not os.path.exists(metrics_file):
            return []
            
        with open(metrics_file, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
                
        return data 