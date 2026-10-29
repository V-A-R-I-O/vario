"""Slice 10 retraining endpoints. Admin role pack is derived from JWT."""
from fastapi import APIRouter,Depends,HTTPException
from app.services.admin_guard import AdminContext,require_admin
from app.services.retraining_service import create_job,get_job
router=APIRouter(prefix="/admin/retrain",tags=["Admin retraining"])
@router.post("",status_code=202)
async def start(admin:AdminContext=Depends(require_admin)):
 try: data=await create_job(admin.role_pack,admin.user_id)
 except ValueError as e: raise HTTPException(status_code=409,detail=str(e)) from e
 return {"status":"success","data":data,"error":None}
@router.get("/{job_id}")
async def status(job_id:str,admin:AdminContext=Depends(require_admin)):
 job=await get_job(job_id,admin.role_pack)
 if job is None: raise HTTPException(status_code=404,detail="Retraining job not found")
 return {"status":"success","data":job,"error":None}
