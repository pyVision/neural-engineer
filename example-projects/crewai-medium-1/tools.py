import requests
import sqlite3
from datetime import datetime
import json
from crewai import Agent, Task
from langchain.tools import tool

base_url="https://api.rss2json.com/v1/api.json?rss_url=https://medium.com/feed"


class MediumTool:

     
    @tool("Get Medium publication data by name and store it to a file")
    def get_data(publication_name: str) -> dict:

        """
        Fetches articles and information from a Medium publication and stores it to a file
        
        Args:
            publication_name: The name of the Medium publication to fetch data from
            
        Returns:
            A dictionary containing the file name in key file_path whose content is publication's feed data 
            
        """
        try:
            print("entering get_data")
            response = requests.get(base_url+"/"+publication_name)
            response.raise_for_status()
            data = response.json()
            
            # Create a unique filename with timestamp and publication name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"medium_data_{publication_name}_{timestamp}"
            
            # Write data to temporary file
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
                
            print(f"completed get_data - saved to {filename}")
            
            #quoted_filename = f"'{filename}'"
            # Return both the data and the filename
            return {
                "file_name": filename
            }
        except requests.exceptions.RequestException as e:
            print(f'An error occurred while fetching data: {e}')
            return {'error': 'An error occurred while fetching data'}

    @tool("Fetches the medium publication content from a file and saves the artcile information and content in a SQLite database")
    def store_articles_in_db(file_name: str=None, db_path: str="database.db") -> str:
        """
        Fetches the medium publication content from a file and saves the artcile information and content in a SQLite database
        
        Args:
            file_name: path to the file 
            db_path: Path to the SQLite database file
            
        Returns:
            A string indicating the result of the operation
        """
        try:
            print("\r\nstoring the data to db ", file_name,db_path)
            # Read the RSS feed data from the file
            with open(file_name, 'r') as f:
                rss_feed = json.load(f)
            
            if 'items' not in rss_feed:
                return "No articles found in the feed"
            
            print("start store_articles_in_db")
            # Connect to SQLite database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS medium_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id TEXT UNIQUE,
                title TEXT,
                author TEXT,
                date TEXT,
                tags TEXT,
                content TEXT,
                url TEXT,
                publication TEXT,
                created_at TIMESTAMP
            )
            ''')
            
            # Process each article
            articles_added = 0
            articles_updated = 0
            
            # Extract publication name from feed data
            publication_name = rss_feed.get('feed', {}).get('title', 'Unknown Publication')
            
            for article in rss_feed['items']:
                article_id = article.get('guid', '')
                title = article.get('title', '')
                author = article.get('author', '')
                date = article.get('pubDate', '')
                tags = json.dumps(article.get('categories', []))
                content = article.get('content', '')
                url = article.get('link', '')
                
                # Check if article already exists
                cursor.execute("SELECT id FROM medium_articles WHERE article_id = ?", (article_id,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing article
                    cursor.execute('''
                    UPDATE medium_articles 
                    SET title = ?, author = ?, date = ?, tags = ?, content = ?, url = ?, 
                        publication = ?, created_at = ?
                    WHERE article_id = ?
                    ''', (title, author, date, tags, content, url, publication_name, 
                          datetime.now().isoformat(), article_id))
                    articles_updated += 1
                else:
                    # Insert new article
                    cursor.execute('''
                    INSERT INTO medium_articles 
                    (article_id, title, author, date, tags, content, url, publication, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (article_id, title, author, date, tags, content, url, 
                          publication_name, datetime.now().isoformat()))
                    articles_added += 1
            
            # Commit changes and close connection
            conn.commit()
            conn.close()
            
            return f"Successfully processed {len(rss_feed['items'])} articles. Added: {articles_added}, Updated: {articles_updated}"
            
        except requests.exceptions.RequestException as e:
            return f"Error fetching data: {str(e)}"
        except sqlite3.Error as e:
            return f"Database error: {str(e)}"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"An unexpected error occurred: {str(e)}"