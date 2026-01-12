"""
Pipeline Scheduler Service - Handles recurring pipeline execution
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class ScheduledPipeline:
    """Represents a scheduled recurring pipeline"""
    pipeline_id: str
    interval_seconds: int
    next_execution: int
    max_executions: int
    execution_count: int
    is_active: bool
    last_execution: Optional[int] = None

class PipelineScheduler:
    """Schedules and executes recurring pipelines"""
    
    def __init__(self, pipeline_executor, safety_service):
        self.pipeline_executor = pipeline_executor
        self.safety_service = safety_service
        self.scheduled_pipelines: Dict[str, ScheduledPipeline] = {}
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    def schedule_pipeline(
        self,
        pipeline_id: str,
        interval_seconds: int,
        max_executions: int
    ) -> ScheduledPipeline:
        """Schedule a pipeline for recurring execution"""
        next_execution = int((datetime.now() + timedelta(seconds=interval_seconds)).timestamp())
        
        scheduled = ScheduledPipeline(
            pipeline_id=pipeline_id,
            interval_seconds=interval_seconds,
            next_execution=next_execution,
            max_executions=max_executions,
            execution_count=0,
            is_active=True
        )
        
        self.scheduled_pipelines[pipeline_id] = scheduled
        
        # Start scheduler if not running
        if not self.running:
            self.start()
        
        return scheduled
    
    def unschedule_pipeline(self, pipeline_id: str) -> bool:
        """Remove a pipeline from scheduling"""
        if pipeline_id in self.scheduled_pipelines:
            self.scheduled_pipelines[pipeline_id].is_active = False
            del self.scheduled_pipelines[pipeline_id]
            return True
        return False
    
    def start(self):
        """Start the scheduler background task"""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._scheduler_loop())
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self._task:
            self._task.cancel()
    
    async def _scheduler_loop(self):
        """Main scheduler loop that checks and executes due pipelines"""
        while self.running:
            try:
                current_time = int(datetime.now().timestamp())
                
                # Check all scheduled pipelines
                for pipeline_id, scheduled in list(self.scheduled_pipelines.items()):
                    if not scheduled.is_active:
                        continue
                    
                    # Check if execution is due
                    if current_time >= scheduled.next_execution:
                        # Check if max executions reached
                        if scheduled.execution_count >= scheduled.max_executions:
                            scheduled.is_active = False
                            continue
                        
                        # Execute pipeline
                        await self._execute_scheduled_pipeline(scheduled)
                        
                        # Update next execution time
                        scheduled.next_execution = current_time + scheduled.interval_seconds
                        scheduled.execution_count += 1
                        scheduled.last_execution = current_time
                
                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)
    
    async def _execute_scheduled_pipeline(self, scheduled: ScheduledPipeline):
        """Execute a scheduled pipeline"""
        try:
            # Get pipeline
            pipeline = self.pipeline_executor.get_pipeline(scheduled.pipeline_id)
            if not pipeline:
                print(f"Pipeline {scheduled.pipeline_id} not found")
                scheduled.is_active = False
                return
            
            # Pre-execution safety check
            safety_result = await self.safety_service.pre_execution_check(
                pipeline_type=pipeline.pipeline_type.value,
                steps=[],  # Would need to convert PipelineStep to dict
                min_total_out=pipeline.min_total_out,
                deadline=pipeline.deadline,
                creator=pipeline.creator
            )
            
            if not safety_result.passed:
                print(f"Pipeline {scheduled.pipeline_id} failed safety check: {safety_result.reason}")
                return
            
            # In production, would need private key from secure storage
            # For now, just log
            print(f"Would execute pipeline {scheduled.pipeline_id} (execution {scheduled.execution_count + 1}/{scheduled.max_executions})")
            
        except Exception as e:
            print(f"Error executing scheduled pipeline {scheduled.pipeline_id}: {e}")
    
    def get_scheduled_pipelines(self) -> List[Dict]:
        """Get all scheduled pipelines"""
        return [
            {
                "pipeline_id": s.pipeline_id,
                "interval_seconds": s.interval_seconds,
                "next_execution": s.next_execution,
                "max_executions": s.max_executions,
                "execution_count": s.execution_count,
                "is_active": s.is_active,
                "last_execution": s.last_execution
            }
            for s in self.scheduled_pipelines.values()
        ]
    
    def get_scheduled_pipeline(self, pipeline_id: str) -> Optional[ScheduledPipeline]:
        """Get a specific scheduled pipeline"""
        return self.scheduled_pipelines.get(pipeline_id)

