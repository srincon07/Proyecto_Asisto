from transformers import pipeline
import logging

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """Spanish sentiment analysis using multilingual BERT"""
    
    def __init__(self):
        try:
            # multilingual model that supports Spanish
            self.classifier = pipeline(
                "sentiment-analysis",
                model="nlptown/bert-base-multilingual-uncased-sentiment",
                device=-1  # CPU; use 0 for GPU if available
            )
        except Exception as e:
            logger.error(f"Error loading sentiment model: {e}")
            self.classifier = None
    
    def analyze(self, text):
        """
        Returns: {
            'label': 'POSITIVE', 'NEUTRAL', or 'NEGATIVE',
            'score': 0.0 to 1.0 (confidence)
        }
        """
        if not self.classifier or not text.strip():
            return {'label': 'NEUTRAL', 'score': 0.0}
        
        try:
            result = self.classifier(text[:512])[0]  # Limit to 512 chars
            label_map = {
                '5 stars': 'POSITIVE',
                '4 stars': 'POSITIVE',
                '3 stars': 'NEUTRAL',
                '2 stars': 'NEGATIVE',
                '1 star': 'NEGATIVE'
            }
            mapped_label = label_map.get(result['label'], 'NEUTRAL')
            return {
                'label': mapped_label,
                'score': result['score']
            }
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return {'label': 'NEUTRAL', 'score': 0.0}

# Singleton instance
_analyzer = None

def get_sentiment_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer