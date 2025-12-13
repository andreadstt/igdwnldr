"""
Twitter Thread Adjuster - Rule-based text splitter for Twitter/X threads
Maximum 280 characters per tweet including spaces
"""
import re
from typing import List, Tuple


class ThreadAdjuster:
    """Split long text into Twitter thread with 280 char limit"""
    
    MAX_LENGTH = 280
    
    # Kata sambung untuk fallback splitting (urutan prioritas dari belakang)
    CONJUNCTIONS = [
        " sehingga ",
        " karena ",
        " dengan ",
        " pada ",
        " dalam ",
        " untuk ",
        " yang "
    ]
    
    # Sentence endings
    SENTENCE_ENDINGS = ('.', '?', '!')
    
    def __init__(self):
        self.url_pattern = re.compile(r'https?://\S+')
        self.hashtag_pattern = re.compile(r'#\w+')
        self.mention_pattern = re.compile(r'@[A-Za-z0-9_.]+')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    def is_balanced_quotes(self, text: str) -> bool:
        """Check if quotes are balanced"""
        double_quotes = text.count('"')
        single_quotes_open = text.count('"')
        single_quotes_close = text.count('"')
        
        # Double quotes must be even
        if double_quotes % 2 != 0:
            return False
        
        # Smart quotes must be balanced
        if single_quotes_open != single_quotes_close:
            return False
        
        return True
    
    def extract_urls(self, text: str) -> Tuple[str, List[str]]:
        """Extract URLs from text and return (text_without_urls, urls_list)"""
        urls = self.url_pattern.findall(text)
        text_without_urls = self.url_pattern.sub('', text).strip()
        return text_without_urls, urls
    
    def extract_hashtags(self, text: str) -> Tuple[str, List[str]]:
        """Extract hashtags from text and return (text_without_hashtags, hashtags_list)"""
        hashtags = self.hashtag_pattern.findall(text)
        text_without_hashtags = self.hashtag_pattern.sub('', text).strip()
        return text_without_hashtags, hashtags
    
    def protect_special_tokens(self, text: str) -> Tuple[str, dict]:
        """Replace mentions, emails, and URLs with placeholders to protect them from splitting
        
        This prevents mentions like @kementerian.atrbpn from being split at the '.'
        
        Returns:
            (protected_text, mapping_dict)
        """
        mapping = {}
        protected_text = text
        counter = 0
        
        # Protect emails first (before mentions, since email contains @)
        for email in self.email_pattern.findall(text):
            placeholder = f"__EMAIL_{counter}__"
            mapping[placeholder] = email
            protected_text = protected_text.replace(email, placeholder, 1)
            counter += 1
        
        # Protect mentions (like @username.with.dots)
        for mention in self.mention_pattern.findall(protected_text):
            placeholder = f"__MENTION_{counter}__"
            mapping[placeholder] = mention
            protected_text = protected_text.replace(mention, placeholder, 1)
            counter += 1
        
        # URLs already extracted separately, but add protection if needed
        for url in self.url_pattern.findall(protected_text):
            placeholder = f"__URL_{counter}__"
            mapping[placeholder] = url
            protected_text = protected_text.replace(url, placeholder, 1)
            counter += 1
        
        return protected_text, mapping
    
    def restore_special_tokens(self, text: str, mapping: dict) -> str:
        """Restore placeholders back to original mentions, emails, and URLs"""
        restored_text = text
        for placeholder, original in mapping.items():
            restored_text = restored_text.replace(placeholder, original)
        return restored_text
    
    def calculate_real_length(self, text: str, token_mapping: dict) -> int:
        """Calculate real length after token restoration
        
        This accounts for the difference between placeholder length and actual token length
        """
        real_text = self.restore_special_tokens(text, token_mapping)
        return len(real_text)
    
    def find_best_split_point(self, text: str, max_len: int) -> int:
        """Find best split point for text within max_len
        
        Priority:
        1. Newline (\\n) - most natural separator
        2. Sentence end (., ?, !)
        3. Conjunction word
        4. Last space before max_len
        """
        if len(text) <= max_len:
            return len(text)
        
        # Get substring up to max_len
        chunk = text[:max_len]
        
        # Priority 1: Find last newline (most natural break)
        last_newline = chunk.rfind('\n')
        if last_newline > 0:
            return last_newline + 1  # Include the newline
        
        # Priority 2: Find last sentence ending
        last_sentence_end = -1
        for ending in self.SENTENCE_ENDINGS:
            pos = chunk.rfind(ending)
            if pos > last_sentence_end:
                last_sentence_end = pos
        
        if last_sentence_end > 0:
            # Include the punctuation mark
            return last_sentence_end + 1
        
        # Priority 3: Find last conjunction before max_len
        best_conjunction_pos = -1
        for conjunction in self.CONJUNCTIONS:
            pos = chunk.rfind(conjunction)
            if pos > best_conjunction_pos:
                best_conjunction_pos = pos
        
        if best_conjunction_pos > 0:
            # Split after the word before conjunction
            return best_conjunction_pos
        
        # Priority 4: Find last space
        last_space = chunk.rfind(' ')
        if last_space > 0:
            return last_space
        
        # Fallback: hard cut at max_len (shouldn't happen with normal text)
        return max_len
    
    def split_text_to_threads(self, text: str) -> List[str]:
        """Split text into thread parts with 280 char limit
        
        BUGFIX: Mentions like @kementerian.atrbpn are protected using placeholders
        to prevent splitting at dots or other punctuation within mentions.
        
        Args:
            text: Long text to split
            
        Returns:
            List of thread parts (each <= 280 chars)
        """
        if not text or not text.strip():
            return []
        
        # STEP 1: Protect special tokens (mentions, emails) with placeholders
        protected_text, token_mapping = self.protect_special_tokens(text)
        
        # STEP 2: Extract URLs (already protected in step 1, but keep for separate thread handling)
        text_without_urls, urls = self.extract_urls(protected_text)
        
        # STEP 3: Extract hashtags
        text_without_hashtags, hashtags = self.extract_hashtags(text_without_urls)
        
        # Clean up text
        text_clean = text_without_hashtags.strip()
        
        threads = []
        remaining = text_clean
        
        while remaining:
            remaining = remaining.strip()
            
            if not remaining:
                break
            
            # Calculate real length after token restoration
            real_length = self.calculate_real_length(remaining, token_mapping)
            
            # If remaining text fits in one tweet (considering real length)
            if real_length <= self.MAX_LENGTH:
                threads.append(remaining)
                break
            
            # Start with a conservative split point
            # We need to find a split point where the REAL length <= 280
            max_safe_len = self.MAX_LENGTH
            split_point = self.find_best_split_point(remaining, max_safe_len)
            
            # Get the chunk and check its real length
            chunk = remaining[:split_point].strip()
            chunk_real_length = self.calculate_real_length(chunk, token_mapping)
            
            # If chunk is too long after restoration, reduce split point
            while chunk_real_length > self.MAX_LENGTH and split_point > 0:
                # Reduce max_safe_len and try again
                max_safe_len = max_safe_len - 20  # Reduce by 20 chars at a time
                if max_safe_len < 50:  # Safety check
                    max_safe_len = 50
                    break
                
                split_point = self.find_best_split_point(remaining, max_safe_len)
                chunk = remaining[:split_point].strip()
                chunk_real_length = self.calculate_real_length(chunk, token_mapping)
            
            # Check if quotes are balanced
            if not self.is_balanced_quotes(chunk):
                # Try to find closing quote within next 280 chars
                search_end = min(len(remaining), split_point + self.MAX_LENGTH)
                search_text = remaining[split_point:search_end]
                
                # Find closing quote
                if '"' in search_text:
                    close_pos = search_text.find('"') + 1
                    split_point = split_point + close_pos
                    chunk = remaining[:split_point].strip()
                elif '"' in search_text:
                    close_pos = search_text.find('"') + 1
                    split_point = split_point + close_pos
                    chunk = remaining[:split_point].strip()
            
            # Validate chunk
            chunk = chunk.strip(' ,')
            
            if chunk:
                threads.append(chunk)
            
            # Move to next part
            remaining = remaining[split_point:].strip()
        
        # STEP 4: Restore special tokens (mentions, emails) from placeholders
        threads = [self.restore_special_tokens(thread, token_mapping) for thread in threads]
        
        # Add URLs as separate threads (if any were extracted separately)
        # Note: URLs in token_mapping are already restored in step 4
        # This is for additional URL handling if needed
        
        # Add hashtags to last thread or create new thread
        if hashtags:
            hashtag_string = ' '.join(hashtags)
            
            if threads:
                last_thread = threads[-1]
                combined = f"{last_thread}\n\n{hashtag_string}"
                
                if len(combined) <= self.MAX_LENGTH:
                    threads[-1] = combined
                else:
                    # Create new thread for hashtags
                    threads.append(hashtag_string)
            else:
                threads.append(hashtag_string)
        
        return threads
    
    def validate_threads(self, threads: List[str]) -> Tuple[bool, List[str]]:
        """Validate threads meet all requirements
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        for i, thread in enumerate(threads):
            # Check length
            if len(thread) > self.MAX_LENGTH:
                errors.append(f"Thread {i+1}: Exceeds 280 chars ({len(thread)} chars)")
            
            # Check leading/trailing spaces or commas
            if thread != thread.strip(' ,'):
                errors.append(f"Thread {i+1}: Has leading/trailing spaces or commas")
            
            # Check empty
            if not thread.strip():
                errors.append(f"Thread {i+1}: Empty thread")
        
        return len(errors) == 0, errors
    
    def adjust_thread(self, text: str) -> dict:
        """Main function to adjust text into threads
        
        Args:
            text: Long text to split
            
        Returns:
            dict with:
                - success: bool
                - threads: List[str]
                - count: int
                - errors: List[str]
        """
        try:
            threads = self.split_text_to_threads(text)
            is_valid, errors = self.validate_threads(threads)
            
            return {
                'success': is_valid,
                'threads': threads,
                'count': len(threads),
                'errors': errors
            }
        except Exception as e:
            return {
                'success': False,
                'threads': [],
                'count': 0,
                'errors': [str(e)]
            }
