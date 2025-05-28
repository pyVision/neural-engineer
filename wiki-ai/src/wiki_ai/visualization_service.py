"""
Repository Visualization Service
Handles background generation and caching of GitHub repository visualization plots
"""
import os
import json
import asyncio
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from .github_analytics import GitHubAnalytics
from .data_controller import get_data_controller


logger = logging.getLogger(__name__)


class VisualizationJobStatus:
    """Enumeration for job statuses"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"


class VisualizationService:
    """Service for managing repository visualization plots"""
    
    def __init__(self, plots_dir: str = "static/plots"):
        self.plots_dir = Path(plots_dir)
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        self.github_analytics = GitHubAnalytics()
        
        # Redis keys for job management
        self.JOBS_KEY_PREFIX = "viz_job"
        self.DATA_CACHE_PREFIX = "viz_data"
        
    async def check_plots_exist(self, owner: str, name: str) -> Dict[str, bool]:
        """
        Check if visualization plots exist for a repository
        
        Returns:
            Dict mapping plot type to existence status
        """
        repo_plots_dir = self.plots_dir / f"{owner}_{name}"
        
        plot_files = {
            "timeline": repo_plots_dir / f"{owner}_{name}_timeline.png",
            "timeline_html": repo_plots_dir / f"{owner}_{name}_timeline.html"
            # "heatmap": repo_plots_dir / f"\{owner}_{name}_heatmap.png",
            # "heatmap_html": repo_plots_dir / f"{owner}_{name}_heatmap.html"
        }
        
        return {
            plot_type: plot_file.exists() 
            for plot_type, plot_file in plot_files.items()
        }
    
    async def get_plot_urls(self, owner: str, name: str) -> Dict[str, Optional[str]]:
        """
        Get URLs for existing plots
        
        Returns:
            Dict mapping plot type to URL (None if doesn't exist)
        """
        plot_exists = await self.check_plots_exist(owner, name)
        
        base_url = f"/static/plots/{owner}_{name}"
        plot_urls = {}
        
        if plot_exists.get("timeline"):
            plot_urls["timeline"] = f"{base_url}/{owner}_{name}_timeline.png"
            plot_urls["timeline_html"] = f"{base_url}/{owner}_{name}_timeline.html"
        else:
            plot_urls["timeline"] = None
            plot_urls["timeline_html"] = None
            
        # if plot_exists.get("heatmap"):
        #     plot_urls["heatmap"] = f"{base_url}/{owner}_{name}_heatmap.png"
        #     plot_urls["heatmap_html"] = f"{base_url}/{owner}_{name}_heatmap.html"
        # else:
        #     plot_urls["heatmap"] = None
        #     plot_urls["heatmap_html"] = None
            
        return plot_urls
    
    async def get_job_status(self, owner: str, name: str) -> Optional[str]:
        """
        Get the current job status for a repository
        
        Returns:
            Job status string or None if no job exists
        """
        data_controller = await get_data_controller()
        job_key = f"{self.JOBS_KEY_PREFIX}:{owner}:{name}"
        
        job_data = await data_controller.cache.get_from_cache(job_key)
        if job_data:
            return job_data.get("status")
        return None
    
    async def set_job_status(self, owner: str, name: str, status: str, 
                           message: str = "", progress: int = 0):
        """
        Set the job status for a repository
        """
        data_controller = await get_data_controller()
        job_key = f"{self.JOBS_KEY_PREFIX}:{owner}:{name}"
        
        job_data = {
            "status": status,
            "message": message,
            "progress": progress,
            "updated_at": datetime.now().isoformat(),
            "owner": owner,
            "name": name
        }
        
        # Cache job status for 1 hour
        await data_controller.cache.set_in_cache(job_key, job_data, ttl=3600)
        logger.info(f"Job status updated for {owner}/{name}: {status} - {message}")
    
    async def is_job_running(self, owner: str, name: str) -> bool:
        """
        Check if a background job is currently running for this repository
        """
        status = await self.get_job_status(owner, name)
        return status in [VisualizationJobStatus.PENDING, VisualizationJobStatus.RUNNING]
    
    async def get_cached_data(self, owner: str, name: str) -> Optional[Dict]:
        """
        Get cached repository data (stars, forks, timeline)
        """
        data_controller = await get_data_controller()
        cache_key = f"{self.DATA_CACHE_PREFIX}:{owner}:{name}"
        
        return await data_controller.cache.get_from_cache(cache_key)
    
    async def cache_data(self, owner: str, name: str, data: Dict, ttl: int = 24*3600):
        """
        Cache repository data with TTL (default 24 hours)
        """
        data_controller = await get_data_controller()
        cache_key = f"{self.DATA_CACHE_PREFIX}:{owner}:{name}"
        
        await data_controller.cache.set_in_cache(cache_key, data, ttl=ttl)
        logger.info(f"Cached repository data for {owner}/{name}")
    
    async def generate_plots_background(self, owner: str, name: str) -> bool:
        """
        Generate plots in the background
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Set initial job status
            await self.set_job_status(
                owner, name, 
                VisualizationJobStatus.RUNNING, 
                "Starting visualization generation...", 
                0
            )
            
            # Check if data exists in cache
            await self.set_job_status(
                owner, name,
                VisualizationJobStatus.RUNNING,
                "Checking cache for existing data...",
                10
            )
            
            cached_data = await self.get_cached_data(owner, name)
            repo_name = f"{owner}/{name}"
            
            if cached_data:
                logger.info(f"Using cached data for {repo_name}")
                await self.set_job_status(
                    owner, name,
                    VisualizationJobStatus.RUNNING,
                    "Using cached data for plot generation...",
                    30
                )
                
                # Use cached data
                timeline_data = cached_data
            else:
                # Fetch fresh data
                await self.set_job_status(
                    owner, name,
                    VisualizationJobStatus.RUNNING,
                    "Fetching repository data from GitHub...",
                    20
                )
                
                logger.info(f"Fetching fresh data for {repo_name}")
                plots, timeline_data = self.github_analytics.generate_all_plots(
                    repo_name, 
                    save_dir=str(self.plots_dir / f"{owner}_{name}")
                )
                
                if timeline_data is None:
                    await self.set_job_status(
                        owner, name,
                        VisualizationJobStatus.FAILED,
                        "Failed to fetch repository data from GitHub API",
                        0
                    )
                    return False
                
                # Cache the data
                await self.cache_data(owner, name, timeline_data)
            
            # Generate plots
            await self.set_job_status(
                owner, name,
                VisualizationJobStatus.RUNNING,
                "Generating timeline visualizations...",
                60
            )
            
            # Create the plots directory for this repo
            repo_plots_dir = self.plots_dir / f"{owner}_{name}"
            repo_plots_dir.mkdir(exist_ok=True)
            
            # Generate timeline plot
            if 'timeline_df' in timeline_data:
                timeline_fig = self.github_analytics.plot_timeline(
                    timeline_data['timeline_df'],
                    repo_name,
                    save_dir=str(repo_plots_dir),
                    milestones_df=timeline_data.get('milestones_df')
                )
                
                await self.set_job_status(
                    owner, name,
                    VisualizationJobStatus.RUNNING,
                    "Generating activity heatmap...",
                    80
                )
                
                # # Generate heatmap if we have stars data
                # if 'stars_df' in timeline_data and not timeline_data['stars_df'].empty:
                #     heatmap_fig = self.github_analytics.plot_activity_heatmap(
                #         timeline_data['stars_df'],
                #         repo_name,
                #         save_dir=str(repo_plots_dir)
                #     )
            
            await self.set_job_status(
                owner, name,
                VisualizationJobStatus.COMPLETED,
                "Visualization generation completed successfully!",
                100
            )
            
            logger.info(f"Successfully generated plots for {repo_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating plots for {owner}/{name}: {str(e)}")
            await self.set_job_status(
                owner, name,
                VisualizationJobStatus.FAILED,
                f"Error: {str(e)}",
                0
            )
            return False
    
    async def initiate_background_generation(self, owner: str, name: str) -> bool:
        """
        Initiate background plot generation if not already running
        
        Returns:
            True if job was started, False if already running
        """
        # Check if job is already running
        if await self.is_job_running(owner, name):
            logger.info(f"Job already running for {owner}/{name}")
            return False
        
        # Start background task
        asyncio.create_task(self.generate_plots_background(owner, name))
        logger.info(f"Initiated background plot generation for {owner}/{name}")
        return True
    
    async def get_visualization_status(self, owner: str, name: str) -> Dict:
        """
        Get comprehensive visualization status for a repository
        
        Returns:
            Dict with plot availability, job status, and URLs
        """
        plot_exists = await self.check_plots_exist(owner, name)
        plot_urls = await self.get_plot_urls(owner, name)
        job_status = await self.get_job_status(owner, name)
        
        # Determine overall status
        if any(plot_exists.values()):
            status = "available"
            message = "Visualizations are available"
        elif job_status in [VisualizationJobStatus.PENDING, VisualizationJobStatus.RUNNING]:
            status = "generating"
            message = "Visualizations are being generated..."
        elif job_status == VisualizationJobStatus.FAILED:
            status = "failed"
            message = "Visualization generation failed"
        else:
            status = "none"
            message = "No visualizations available"
        
        return {
            "status": status,
            "message": message,
            "plots_exist": plot_exists,
            "plot_urls": plot_urls,
            "job_status": job_status,
            "has_timeline": plot_exists.get("timeline", False),
            "has_heatmap": False
        }


# Global instance
_visualization_service = None

def get_visualization_service() -> VisualizationService:
    """Get singleton visualization service instance"""
    global _visualization_service
    if _visualization_service is None:
        _visualization_service = VisualizationService()
    return _visualization_service
