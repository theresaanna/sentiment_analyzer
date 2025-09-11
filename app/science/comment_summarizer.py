"""
Enhanced Comment Summarization with Intelligent Context-Aware Filtering.
"""
import os
import re
import logging
from typing import List, Dict, Optional, Set, Tuple
from collections import Counter
import math
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import openai
from app.cache import cache

logger = logging.getLogger(__name__)


class EnhancedCommentSummarizer:
    """Enhanced AI-powered comment summarizer with video context awareness."""
    
    def __init__(self, use_openai: bool = False):
        """
        Initialize the enhanced comment summarizer.
        
        Args:
            use_openai: Whether to use OpenAI API for summarization
        """
        self.use_openai = use_openai and os.getenv('OPENAI_API_KEY')
        
        if self.use_openai:
            openai.api_key = os.getenv('OPENAI_API_KEY')
            logger.info("Using OpenAI for enhanced comment summarization")
        else:
            # Use open-source summarization model
            logger.info("Loading BART model for enhanced comment summarization...")
            self.model_name = "facebook/bart-large-cnn"
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            self.summarizer = pipeline(
                "summarization",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if os.environ.get('CUDA_VISIBLE_DEVICES') else -1
            )
    
    def _extract_context_aware_stopwords(self, video_info: Dict) -> Set[str]:
        """
        Extract video-specific stop words based on video metadata for social media analysis.
        
        Args:
            video_info: Dictionary containing video metadata
            
        Returns:
            Set of context-specific stop words
        """
        context_stopwords = set()
        
        if video_info:
            # Extract from title with enhanced parsing
            if 'title' in video_info:
                title = video_info['title'].lower()
                title_words = re.findall(r'\b[a-z]+\b', title)
                
                # Add all title words and common variations
                for word in title_words:
                    if len(word) > 2:
                        context_stopwords.add(word)
                        # Add plural/singular variations
                        if word.endswith('s'):
                            context_stopwords.add(word[:-1])
                        elif not word.endswith('s'):
                            context_stopwords.add(word + 's')
                        # Add possessive forms
                        context_stopwords.add(word + "s")
            
            # Extract channel name with variations
            if 'channel' in video_info:
                channel_words = re.findall(r'\b[a-z]+\b', video_info['channel'].lower())
                for word in channel_words:
                    context_stopwords.add(word)
                    if len(word) > 3:
                        # Add common channel name variations
                        context_stopwords.update([word + 's', word[:-1] if word.endswith('s') else word])
                        context_stopwords.update([word + 'tv', word + 'official', word + 'music'])
            
            # Enhanced artist/creator pattern detection
            if 'title' in video_info:
                title = video_info['title']
                
                # More comprehensive artist patterns
                artist_patterns = [
                    r'^([^-:]+?)(?:\s*[-:])',  # Before dash
                    r'^([^:]+?)(?:\s*:)',      # Before colon
                    r'feat(?:uring)?\.?\s+([^,\(\)\[\]]+)',  # Featured artists
                    r'ft\.?\s+([^,\(\)\[\]]+)',    # Ft. variations
                    r'with\s+([^,\(\)\[\]]+)',     # "with Artist"
                    r'by\s+([^,\(\)\[\]]+)',       # "by Artist"
                    r'\(([^\)]+)\s+(?:remix|version|cover)\)',  # Remix artists
                ]
                
                for pattern in artist_patterns:
                    matches = re.findall(pattern, title, re.IGNORECASE)
                    for match in matches:
                        artist_words = re.findall(r'\b[a-z]+\b', match.lower())
                        context_stopwords.update(artist_words)
                        # Add variations for each artist word
                        for word in artist_words:
                            if len(word) > 2:
                                context_stopwords.update([word + 's', word + "'s", word + 'es'])
                
                # Comprehensive artist-specific handling
                artist_mappings = {
                    'lady gaga': ['lady', 'gaga', 'ladygaga', 'gagas', 'stefani', 'germanotta'],
                    'taylor swift': ['taylor', 'swift', 'tay', 'ts', 'swifties', 'swiftie'],
                    'beyonce': ['beyonce', 'bey', 'queen', 'beyhive', 'knowles', 'carter'],
                    'drake': ['drake', 'drizzy', 'aubrey', 'graham', 'ovo'],
                    'ariana grande': ['ariana', 'grande', 'ari', 'arianas', 'grandes'],
                    'justin bieber': ['justin', 'bieber', 'biebs', 'believers'],
                    'ed sheeran': ['sheeran', 'ed', 'eddie'],
                    'billie eilish': ['billie', 'eilish', 'william'],
                    'the weeknd': ['weeknd', 'weeknd', 'abel', 'tesfaye'],
                    'dua lipa': ['dua', 'lipa'],
                    'post malone': ['post', 'malone', 'posty'],
                    'bruno mars': ['bruno', 'mars'],
                    'adele': ['adele', 'adkins'],
                    'rihanna': ['rihanna', 'riri', 'fenty', 'robyn'],
                    'eminem': ['eminem', 'marshall', 'mathers', 'slim', 'shady'],
                    'kendrick lamar': ['kendrick', 'lamar', 'kdot'],
                }
                
                title_lower = title.lower()
                for artist_name, variations in artist_mappings.items():
                    if artist_name in title_lower:
                        context_stopwords.update(variations)
                
                # Remove common video format indicators
                format_indicators = [
                    'official', 'music', 'video', 'mv', 'hd', 'hq', '4k', 'lyric', 'lyrics',
                    'audio', 'live', 'performance', 'session', 'acoustic', 'remix', 'cover',
                    'version', 'extended', 'radio', 'edit', 'explicit', 'clean', 'instrumental',
                    'karaoke', 'reaction', 'review', 'analysis', 'breakdown', 'behind', 'scenes',
                    'making', 'studio', 'session', 'interview', 'documentary', 'trailer', 'teaser',
                    'premiere', 'first', 'time', 'listening', 'hearing'
                ]
                context_stopwords.update(format_indicators)
        
        # Enhanced platform and social media terms
        platform_terms = [
            'video', 'youtube', 'channel', 'subscribe', 'like', 'comment', 'share', 'follow',
            'notification', 'bell', 'thumbs', 'views', 'subscribers', 'content', 'creator',
            'youtuber', 'vlog', 'blog', 'stream', 'streaming', 'live', 'chat', 'trending',
            'viral', 'algorithm', 'recommended', 'suggestion', 'playlist', 'queue'
        ]
        context_stopwords.update(platform_terms)
        
        # Add common reaction/engagement words that don't provide topic insights
        reaction_words = [
            'omg', 'wow', 'yeah', 'yes', 'no', 'lol', 'lmao', 'haha', 'crying', 'dead',
            'literally', 'actually', 'really', 'totally', 'absolutely', 'definitely',
            'probably', 'maybe', 'perhaps', 'honestly', 'truly', 'seriously',
            'amazing', 'awesome', 'incredible', 'fantastic', 'wonderful', 'perfect',
            'terrible', 'awful', 'horrible', 'bad', 'good', 'great', 'best', 'worst'
        ]
        context_stopwords.update(reaction_words)
        
        return context_stopwords
    
    def _calculate_tfidf_scores(self, documents: List[str]) -> Dict[str, float]:
        """
        Calculate TF-IDF scores for words across documents.
        
        Args:
            documents: List of text documents (comments)
            
        Returns:
            Dictionary of word -> TF-IDF score
        """
        # Calculate document frequency
        doc_freq = Counter()
        word_freq_per_doc = []
        total_docs = len(documents)
        
        for doc in documents:
            words = set(re.findall(r'\b[a-z]+\b', doc.lower()))
            word_freq_per_doc.append(Counter(re.findall(r'\b[a-z]+\b', doc.lower())))
            for word in words:
                doc_freq[word] += 1
        
        # Calculate TF-IDF
        tfidf_scores = {}
        
        for doc_idx, word_freq in enumerate(word_freq_per_doc):
            total_words = sum(word_freq.values())
            for word, freq in word_freq.items():
                tf = freq / total_words if total_words > 0 else 0
                idf = math.log(total_docs / (1 + doc_freq[word]))
                
                if word not in tfidf_scores:
                    tfidf_scores[word] = 0
                tfidf_scores[word] += tf * idf
        
        # Normalize scores
        if tfidf_scores:
            max_score = max(tfidf_scores.values())
            if max_score > 0:
                for word in tfidf_scores:
                    tfidf_scores[word] /= max_score
        
        return tfidf_scores
    
    def _extract_intelligent_themes(self, 
                                  comments: List[Dict], 
                                  video_info: Optional[Dict] = None,
                                  top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Extract themes using TF-IDF and context-aware filtering.
        
        Args:
            comments: List of comment dictionaries
            video_info: Optional video metadata
            top_n: Number of top themes to return
            
        Returns:
            List of (theme, relevance_score) tuples
        """
        # Base stop words
        stop_words = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
                         'to', 'for', 'of', 'with', 'by', 'from', 'is', 'was', 
                         'are', 'were', 'been', 'be', 'have', 'has', 'had', 
                         'do', 'does', 'did', 'will', 'would', 'could', 'should',
                         'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
                         'it', 'we', 'they', 'what', 'which', 'who', 'when', 'where',
                         'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
                         'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
                         'own', 'same', 'so', 'than', 'too', 'very', 'can', 'just',
                         'get', 'got', 'also', 'really', 'much', 'even', 'back',
                         'know', 'think', 'see', 'make', 'want', 'look', 'use',
                         'her', 'him', 'them', 'us', 'me', 'my', 'your', 'their'])
        
        # Add context-specific stop words
        if video_info:
            context_stopwords = self._extract_context_aware_stopwords(video_info)
            stop_words.update(context_stopwords)
        
        # Prepare documents for TF-IDF
        documents = [c.get('text', '') for c in comments if c.get('text', '')]
        
        # Calculate TF-IDF scores
        tfidf_scores = self._calculate_tfidf_scores(documents)
        
        # Filter and rank themes
        filtered_themes = []
        for word, score in tfidf_scores.items():
            # Apply filters
            if (len(word) > 3 and 
                word not in stop_words and
                not word.isdigit() and
                score > 0.1):  # Minimum relevance threshold
                filtered_themes.append((word, score))
        
        # Sort by score and return top N
        filtered_themes.sort(key=lambda x: x[1], reverse=True)
        
        return filtered_themes[:top_n]
    
    def _identify_controversy_and_debates(self, 
                                         comments: List[Dict],
                                         sentiment_results: Optional[Dict] = None) -> Dict:
        """
        Identify controversial topics and debates in comments.
        
        Args:
            comments: List of comment dictionaries
            sentiment_results: Optional sentiment analysis results
            
        Returns:
            Dictionary with controversy analysis
        """
        controversy_indicators = {
            'debate_words': ['disagree', 'wrong', 'actually', 'but', 'however', 
                           'although', 'nevertheless', 'contrary', 'versus', 'vs'],
            'strong_opinions': ['hate', 'love', 'terrible', 'amazing', 'worst', 
                              'best', 'disgusting', 'perfect', 'awful', 'brilliant'],
            'question_marks': 0,
            'exclamation_marks': 0,
            'caps_usage': 0
        }
        
        controversial_topics = []
        debate_threads = []
        
        for i, comment in enumerate(comments):
            text = comment.get('text', '').lower()
            
            # Count indicators
            controversy_indicators['question_marks'] += text.count('?')
            controversy_indicators['exclamation_marks'] += text.count('!')
            
            # Check for CAPS usage (shouting)
            original_text = comment.get('text', '')
            caps_words = [w for w in original_text.split() if w.isupper() and len(w) > 2]
            controversy_indicators['caps_usage'] += len(caps_words)
            
            # Identify potential controversial statements
            if sentiment_results and i < len(sentiment_results.get('individual_results', [])):
                sentiment = sentiment_results['individual_results'][i]
                confidence = sentiment.get('confidence', 0)
                
                # High confidence negative or very polarized comments
                if (sentiment['predicted_sentiment'] == 'negative' and confidence > 0.8) or \
                   any(word in text for word in controversy_indicators['strong_opinions']):
                    controversial_topics.append({
                        'text': text[:200],
                        'sentiment': sentiment['predicted_sentiment'],
                        'confidence': confidence,
                        'comment_id': sentiment.get('comment_id', None),
                        'index': i
                    })
            
            # Identify debate threads (replies with opposing views)
            if comment.get('is_reply', False):
                if any(word in text for word in controversy_indicators['debate_words']):
                    debate_threads.append(text[:150])
        
        return {
            'controversy_score': self._calculate_controversy_score(controversy_indicators, len(comments)),
            'controversial_topics': controversial_topics[:5],
            'debate_threads': debate_threads[:3],
            'indicators': controversy_indicators
        }
    
    def _calculate_controversy_score(self, indicators: Dict, total_comments: int) -> float:
        """
        Calculate a controversy score from 0 to 1.
        
        Args:
            indicators: Dictionary of controversy indicators
            total_comments: Total number of comments
            
        Returns:
            Controversy score
        """
        if total_comments == 0:
            return 0.0
        
        # Normalize indicators
        question_ratio = indicators['question_marks'] / total_comments
        exclamation_ratio = indicators['exclamation_marks'] / total_comments
        caps_ratio = indicators['caps_usage'] / total_comments
        
        # Weight and combine
        score = (
            min(question_ratio * 2, 1.0) * 0.3 +
            min(exclamation_ratio * 2, 1.0) * 0.3 +
            min(caps_ratio * 5, 1.0) * 0.4
        )
        
        return min(score, 1.0)
    
    def _extract_social_media_themes(self, 
                                   comments: List[Dict], 
                                   video_info: Optional[Dict] = None,
                                   top_n: int = 15) -> Dict[str, any]:
        """
        Extract themes specifically for social media managers with insights.
        
        Args:
            comments: List of comment dictionaries
            video_info: Optional video metadata
            top_n: Number of top themes to return
            
        Returns:
            Dictionary with structured themes and insights
        """
        # Base stop words (comprehensive)
        stop_words = set([
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'from', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us',
            'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'what', 'which', 'who',
            'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
            'too', 'very', 'just', 'now', 'get', 'go', 'know', 'see', 'think', 'say', 'come',
            'want', 'look', 'make', 'take', 'one', 'two', 'first', 'last', 'long', 'little',
            'much', 'many', 'new', 'old', 'right', 'wrong', 'big', 'small', 'also', 'back',
            'work', 'way', 'even', 'well', 'still', 'after', 'over', 'never', 'here', 'there',
            'part', 'feel', 'show', 'find', 'keep', 'put', 'give', 'try', 'call', 'ask',
            'turn', 'move', 'play', 'run', 'seem', 'need', 'want', 'tell', 'hand', 'high',
            'every', 'large', 'add', 'start', 'might', 'between'
        ])
        
        # Add video-specific context stopwords
        if video_info:
            context_stopwords = self._extract_context_aware_stopwords(video_info)
            stop_words.update(context_stopwords)
        
        # Prepare documents for analysis
        documents = [c.get('text', '') for c in comments if c.get('text', '')]
        
        if not documents:
            return {
                'themes': [],
                'insights': {
                    'total_themes': 0,
                    'hot_topics': 0,
                    'emotional_themes': 0,
                    'high_engagement': 0,
                    'coverage_analysis': {
                        'most_discussed': None,
                        'audience_focus': 'No discussion data available',
                        'content_opportunities': ['Generate more engaging content to encourage discussion']
                    }
                }
            }
        
        # Calculate word frequencies across all documents
        all_words = []
        for doc in documents:
            # Clean and tokenize
            cleaned = re.sub(r'[^a-zA-Z\s]', ' ', doc.lower())
            words = [w for w in cleaned.split() if len(w) > 3 and w not in stop_words]
            all_words.extend(words)
        
        # Count frequencies
        word_freq = Counter(all_words)
        
        # Calculate TF-IDF scores for better relevance
        tfidf_scores = self._calculate_tfidf_scores(documents)
        
        # Combine frequency and TF-IDF for final scoring
        theme_scores = {}
        # Adjust frequency threshold based on dataset size
        min_freq = max(1, min(2, len(documents) // 10))  # At least 1, but scale with dataset size
        
        for word, freq in word_freq.items():
            if freq >= min_freq and word in tfidf_scores:  
                # Weighted score: frequency (40%) + TF-IDF relevance (60%)
                theme_scores[word] = (freq * 0.4) + (tfidf_scores[word] * 0.6 * 100)
        
        # Sort and get top themes
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        # Check if we have enough meaningful themes
        if len(sorted_themes) < 2:
            return {
                'themes': [],
                'insights': {
                    'total_themes': 0,
                    'hot_topics': 0,
                    'emotional_themes': 0,
                    'high_engagement': 0,
                    'coverage_analysis': {
                        'most_discussed': None,
                        'audience_focus': 'Limited discussion variety - mostly brief reactions',
                        'content_opportunities': [
                            'Encourage more detailed discussions in future content',
                            'Ask specific questions to prompt audience engagement'
                        ]
                    }
                }
            }
        
        # Categorize themes for social media insights
        themes_with_insights = []
        emotional_words = set(['love', 'hate', 'angry', 'happy', 'sad', 'excited', 'disappointed', 
                              'frustrated', 'proud', 'grateful', 'nostalgic', 'emotional', 'feelings'])
        trending_indicators = set(['viral', 'trending', 'popular', 'everywhere', 'everyone', 'talking'])
        
        for word, score in sorted_themes:
            frequency = word_freq[word]
            
            # Determine category
            category = 'General Discussion'
            if word in emotional_words or any(emo in word for emo in ['feel', 'emotion', 'mood']):
                category = 'Emotional Response'
            elif word in trending_indicators:
                category = 'Trending Topic'
            elif frequency > len(comments) * 0.1:  # Appears in >10% of comments
                category = 'Hot Topic'
            elif word in ['new', 'latest', 'recent', 'update', 'changed']:
                category = 'Recent Development'
            elif word in ['years', 'always', 'never', 'remember', 'used', 'before', 'nostalgia']:
                category = 'Historical Context'
            
            # Calculate engagement potential (adjust thresholds based on dataset size)
            engagement_potential = 'Low'
            if len(comments) < 10:  # Small datasets need different thresholds
                if frequency >= 2:
                    engagement_potential = 'High'
                elif frequency >= 1:
                    engagement_potential = 'Medium'
            else:  # Larger datasets use percentage-based thresholds
                if frequency > len(comments) * 0.15:
                    engagement_potential = 'High'
                elif frequency > len(comments) * 0.05:
                    engagement_potential = 'Medium'
            
            themes_with_insights.append({
                'word': word,
                'frequency': frequency,
                'score': round(score, 2),
                'category': category,
                'engagement_potential': engagement_potential,
                'percentage': round((frequency / len(comments)) * 100, 1)
            })
        
        # Generate insights for social media managers
        insights = {
            'total_themes': len(themes_with_insights),
            'hot_topics': len([t for t in themes_with_insights if t['category'] == 'Hot Topic']),
            'emotional_themes': len([t for t in themes_with_insights if t['category'] == 'Emotional Response']),
            'high_engagement': len([t for t in themes_with_insights if t['engagement_potential'] == 'High']),
            'coverage_analysis': {
                'most_discussed': themes_with_insights[0]['word'] if themes_with_insights else None,
                'audience_focus': self._determine_audience_focus(themes_with_insights),
                'content_opportunities': self._identify_content_opportunities(themes_with_insights)
            }
        }
        
        return {
            'themes': themes_with_insights,
            'insights': insights
        }
    
    def _determine_audience_focus(self, themes: List[Dict]) -> str:
        """Determine the primary audience focus based on themes."""
        if not themes:
            return 'Mixed audience interests'
        
        emotional_count = sum(1 for t in themes if t['category'] == 'Emotional Response')
        trending_count = sum(1 for t in themes if t['category'] == 'Trending Topic')
        hot_topic_count = sum(1 for t in themes if t['category'] == 'Hot Topic')
        
        if emotional_count > len(themes) * 0.4:
            return 'Emotionally engaged audience'
        elif trending_count > len(themes) * 0.3:
            return 'Trend-conscious audience'
        elif hot_topic_count > len(themes) * 0.5:
            return 'Highly active discussion community'
        else:
            return 'Diverse audience interests'
    
    def _identify_content_opportunities(self, themes: List[Dict]) -> List[str]:
        """Identify content creation opportunities from themes."""
        opportunities = []
        
        if not themes:
            return opportunities
        
        high_engagement_themes = [t for t in themes if t['engagement_potential'] == 'High']
        emotional_themes = [t for t in themes if t['category'] == 'Emotional Response']
        hot_topics = [t for t in themes if t['category'] == 'Hot Topic']
        
        if high_engagement_themes:
            top_theme = high_engagement_themes[0]['word']
            opportunities.append(f"Create content around '{top_theme}' - high audience engagement")
        
        if emotional_themes:
            opportunities.append("Leverage emotional connection opportunities in future content")
        
        if hot_topics:
            opportunities.append("Consider addressing trending discussion topics in upcoming videos")
        
        if len(themes) > 10:
            opportunities.append("Rich discussion diversity suggests engaged, active community")
        
        return opportunities[:3]  # Limit to top 3 opportunities
    
    def _generate_detailed_insights(self,
                                  comments: List[Dict],
                                  sentiment_results: Optional[Dict],
                                  themes: List[Tuple[str, float]],
                                  controversy: Dict,
                                  video_info: Optional[Dict]) -> str:
        """
        Generate detailed, verbose insights about the comments.
        
        Args:
            comments: List of comment dictionaries
            sentiment_results: Sentiment analysis results
            themes: List of extracted themes with scores
            controversy: Controversy analysis
            video_info: Video metadata
            
        Returns:
            Detailed insights text
        """
        insights = []
        
        # Sentiment distribution with nuance
        if sentiment_results:
            pos_pct = sentiment_results.get('sentiment_percentages', {}).get('positive', 0)
            neg_pct = sentiment_results.get('sentiment_percentages', {}).get('negative', 0)
            neu_pct = sentiment_results.get('sentiment_percentages', {}).get('neutral', 0)
            
            sentiment_desc = self._describe_sentiment_distribution(pos_pct, neg_pct, neu_pct)
            insights.append(f"\n📊 SENTIMENT LANDSCAPE: {sentiment_desc}")
            
            # Confidence analysis
            avg_confidence = sentiment_results.get('average_confidence', 0)
            if avg_confidence > 0.8:
                insights.append("The sentiment signals are strong and clear, indicating viewers have definitive opinions.")
            elif avg_confidence < 0.6:
                insights.append("The sentiment signals show ambiguity, suggesting nuanced or mixed feelings among viewers.")
        
        # Theme analysis with context - limited to top 5 for readability
        if themes:
            theme_desc = "\n🎯 KEY DISCUSSION THEMES:\n"
            for i, (theme, score) in enumerate(themes[:5], 1):
                relevance = "High relevance" if score > 0.7 else "Moderate relevance" if score > 0.4 else "Emerging topic"
                theme_desc += f"  {i}. '{theme}' - {relevance} (score: {score:.2f})\n"
            insights.append(theme_desc)
        
        # Dynamic reception analysis based on sentiment and controversy
        if sentiment_results:
            pos_pct = sentiment_results.get('sentiment_percentages', {}).get('positive', 0)
            neg_pct = sentiment_results.get('sentiment_percentages', {}).get('negative', 0)
            
            # Determine reception type
            if controversy['controversy_score'] > 0.3:
                insights.append(f"\n⚡ CONTROVERSY DETECTED:")
                insights.append(f"  Controversy level: {'High' if controversy['controversy_score'] > 0.6 else 'Moderate'} ({controversy['controversy_score']:.2f})")
                
                if controversy['controversial_topics']:
                    insights.append("  Divisive comments identified in discussion")
            elif pos_pct > 80:
                insights.append(f"\n🎆 OVERWHELMINGLY POSITIVE RECEPTION:")
                insights.append(f"  Viewer approval: {pos_pct:.1f}% positive sentiment")
                insights.append("  Strong consensus and appreciation from the audience")
            elif pos_pct > 60 and neg_pct < 20:
                insights.append(f"\n✅ POSITIVE RECEPTION:")
                insights.append(f"  Viewer approval: {pos_pct:.1f}% positive sentiment")
                insights.append("  Generally well-received with minimal criticism")
            elif abs(pos_pct - neg_pct) < 15:
                insights.append(f"\n🤔 MIXED RECEPTION:")
                insights.append(f"  Balanced response: {pos_pct:.1f}% positive, {neg_pct:.1f}% negative")
                insights.append("  Content sparked diverse reactions and opinions")
            elif neg_pct > 50:
                insights.append(f"\n⚠️ CRITICAL RECEPTION:")
                insights.append(f"  Viewer criticism: {neg_pct:.1f}% negative sentiment")
                insights.append("  Content received significant pushback from viewers")
        
        return "\n".join(insights)
    
    def _describe_sentiment_distribution(self, pos_pct: float, neg_pct: float, neu_pct: float) -> str:
        """
        Create a nuanced description of sentiment distribution.
        
        Args:
            pos_pct: Positive percentage
            neg_pct: Negative percentage  
            neu_pct: Neutral percentage
            
        Returns:
            Descriptive text
        """
        if pos_pct > 70:
            return f"Overwhelmingly positive reception ({pos_pct:.1f}% positive), with viewers expressing strong appreciation and support. Limited criticism ({neg_pct:.1f}% negative) suggests broad appeal."
        elif pos_pct > 50:
            return f"Generally positive response ({pos_pct:.1f}% positive) with notable areas of criticism ({neg_pct:.1f}% negative), indicating a favorable but not unanimous reception."
        elif neg_pct > 50:
            return f"Predominantly critical response ({neg_pct:.1f}% negative) with some supporters ({pos_pct:.1f}% positive), suggesting controversial or divisive content."
        elif abs(pos_pct - neg_pct) < 10:
            return f"Highly polarized response with nearly equal positive ({pos_pct:.1f}%) and negative ({neg_pct:.1f}%) reactions, indicating the content is divisive."
        else:
            return f"Mixed reception with {pos_pct:.1f}% positive, {neg_pct:.1f}% negative, and {neu_pct:.1f}% neutral responses, showing diverse viewer perspectives."
    
    def generate_enhanced_summary(self, 
                                 comments: List[Dict], 
                                 sentiment_results: Optional[Dict] = None,
                                 video_info: Optional[Dict] = None) -> Dict:
        """
        Generate an enhanced, intelligent summary of comments.
        
        Args:
            comments: List of comment dictionaries
            sentiment_results: Optional sentiment analysis results
            video_info: Optional video metadata for context
            
        Returns:
            Dictionary containing enhanced summary and metadata
        """
        if not comments:
            return {
                'summary': "No comments available to summarize.",
                'method': 'none',
                'comments_analyzed': 0
            }
        
        # Extract intelligent themes with TF-IDF
        themes = self._extract_intelligent_themes(comments, video_info, top_n=10)
        
        # Analyze controversy and debates
        controversy = self._identify_controversy_and_debates(comments, sentiment_results)
        
        # Generate detailed insights
        detailed_insights = self._generate_detailed_insights(
            comments, sentiment_results, themes, controversy, video_info
        )
        
        # Create the main summary
        if self.use_openai:
            summary = self._generate_openai_summary(
                comments, sentiment_results, themes, controversy, video_info, detailed_insights
            )
        else:
            summary = self._generate_local_summary(
                comments, sentiment_results, themes, controversy, video_info, detailed_insights
            )
        
        # Extract social media themes for managers
        try:
            social_themes = self._extract_social_media_themes(comments, video_info, top_n=15)
            logger.info(f"Generated {len(social_themes.get('themes', []))} social media themes")
        except Exception as e:
            logger.error(f"Error extracting social media themes: {e}")
            social_themes = {'themes': [], 'insights': {'total_themes': 0}}
        
        # Add enhanced metadata
        summary['detailed_insights'] = detailed_insights
        summary['intelligent_themes'] = [(theme, score) for theme, score in themes[:5]]
        summary['social_media_themes'] = social_themes  # New structured themes for UI
        summary['controversy_analysis'] = {
            'score': controversy['controversy_score'],
            'level': 'High' if controversy['controversy_score'] > 0.6 else 
                    'Moderate' if controversy['controversy_score'] > 0.3 else 'Low',
            'topics': controversy.get('controversial_topics', [])
        }
        summary['video_context'] = video_info.get('title', 'Unknown') if video_info else 'Unknown'
        summary['video_id'] = video_info.get('id', None) if video_info else None
        
        return summary
    
    def _generate_openai_summary(self, comments, sentiment_results, themes, controversy, video_info, insights):
        """Generate summary using OpenAI with enhanced context."""
        try:
            # Prepare enhanced prompt
            theme_list = ", ".join([t[0] for t in themes[:5]])
            
            video_context = ""
            if video_info:
                video_context = f"""
                Video: {video_info.get('title', 'Unknown')}
                Channel: {video_info.get('channel', 'Unknown')}
                """
            
            prompt = f"""
            Provide a comprehensive, detailed analysis of YouTube video comments with intelligent insights.
            
            {video_context}
            
            Key Themes (via TF-IDF analysis): {theme_list}
            Controversy Level: {controversy['controversy_score']:.2f}
            
            {insights}
            
            Based on the above analysis, create a detailed summary that:
            1. Provides a nuanced overview of viewer reception (3-4 sentences)
            2. Identifies and explains the main discussion topics (not just listing them)
            3. Highlights specific praise and criticism with context
            4. Notes any demographic or community patterns if detectable
            5. Discusses controversial aspects and debates if present
            6. Provides actionable insights for content creators
            
            Make the summary verbose and insightful, going beyond surface-level observations.
            Use specific examples and percentages where relevant.
            Focus on meaningful patterns rather than obvious observations.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert social media analyst specializing in YouTube comment analysis. Provide detailed, nuanced insights that go beyond basic sentiment to understand viewer psychology, community dynamics, and content reception patterns."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            return {
                'summary': response.choices[0].message.content,
                'method': 'openai_enhanced',
                'comments_analyzed': len(comments)
            }
            
        except Exception as e:
            logger.error(f"Error using OpenAI API: {e}")
            return self._generate_local_summary(
                comments, sentiment_results, themes, controversy, video_info, insights
            )
    
    def _generate_local_summary(self, comments, sentiment_results, themes, controversy, video_info, insights):
        """Generate summary using local processing with enhanced analysis."""
        # Just return the insights as the main summary - they're already comprehensive
        return {
            'summary': insights,
            'method': 'local_enhanced',
            'comments_analyzed': len(comments)
        }
    
    def _get_diverse_samples(self, comments, sentiment_results):
        """Get diverse comment samples for each sentiment category."""
        samples = {
            'Highly Positive': None,
            'Constructive Criticism': None,
            'Neutral Observer': None
        }
        
        for i, result in enumerate(sentiment_results[:100]):  # Limit to first 100
            if i >= len(comments):
                break
                
            comment_text = comments[i].get('text', '')
            sentiment = result['predicted_sentiment']
            confidence = result.get('confidence', 0)
            
            if sentiment == 'positive' and confidence > 0.8 and not samples['Highly Positive']:
                samples['Highly Positive'] = comment_text
            elif sentiment == 'negative' and confidence > 0.6 and not samples['Constructive Criticism']:
                if not any(curse in comment_text.lower() for curse in ['hate', 'stupid', 'dumb', 'worst']):
                    samples['Constructive Criticism'] = comment_text
            elif sentiment == 'neutral' and not samples['Neutral Observer']:
                samples['Neutral Observer'] = comment_text
            
            if all(samples.values()):
                break
        
        return samples


# Backward compatibility wrapper
class CommentSummarizer(EnhancedCommentSummarizer):
    """Wrapper for backward compatibility."""
    
    def generate_summary(self, comments: List[Dict], sentiment_results: Optional[Dict] = None) -> Dict:
        """
        Generate a comprehensive summary of comments.
        Wrapper method for backward compatibility.
        """
        # Try to get video info from cache if available
        video_info = None
        if comments and len(comments) > 0:
            # Try to extract video ID from comment metadata if available
            # This is a placeholder - actual implementation would need video_id passed
            pass
        
        return self.generate_enhanced_summary(comments, sentiment_results, video_info)
    
    def _extract_themes(self, comments: List[Dict], top_n: int = 5) -> List[str]:
        """
        Extract key themes from comments.
        Wrapper method for backward compatibility.
        """
        themes = self._extract_intelligent_themes(comments, None, top_n)
        return [theme[0] for theme in themes]
    
    def _calculate_engagement_metrics(self, comments: List[Dict]) -> Dict:
        """
        Calculate engagement metrics from comments.
        Maintains backward compatibility.
        """
        total_likes = sum(c.get('likes', 0) for c in comments)
        avg_likes = total_likes / len(comments) if comments else 0
        
        most_liked = max(comments, key=lambda c: c.get('likes', 0)) if comments else None
        
        replies = sum(1 for c in comments if c.get('is_reply', False))
        reply_rate = (replies / len(comments) * 100) if comments else 0
        
        return {
            'total_likes': total_likes,
            'average_likes': round(avg_likes, 2),
            'most_liked_comment': most_liked.get('text', '')[:200] if most_liked else '',
            'most_liked_count': most_liked.get('likes', 0) if most_liked else 0,
            'reply_rate': round(reply_rate, 2)
        }
