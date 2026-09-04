from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status

from app.models.user import User
from app.models.product import Product
from app.models.inspection import Inspection
from app.models.evidence import Evidence
from app.schemas.inspection import InspectionUploadResponse, ImageUploadResponse
from app.services.storage_service import storage_service

class InspectionService:
    async def create_inspection_from_upload(
        self,
        db: Session,
        image: UploadFile,
        product_name: str,
        category: str,
        brand: str | None = None
    ) -> InspectionUploadResponse:
        
        # 0. Get or create a default user (since auth isn't implemented yet)
        user = db.query(User).first()
        if not user:
            user = User(username="default_officer", email="officer@example.com")
            db.add(user)
            db.commit()
            db.refresh(user)

        # 1. Save and validate image
        file_path, filename, content_type = await storage_service.save_upload(image)
        
        try:
            # 2. Create Product
            product = Product(
                name=product_name or "Unknown Product",
                category=category or "unknown",
                brand=brand
            )
            db.add(product)
            db.flush() # Get ID without committing

            # 3. Create Inspection
            inspection = Inspection(
                product_id=product.id,
                inspector_id=user.id,
                status="PENDING"
            )
            db.add(inspection)
            db.flush()

            # 4. Create Evidence metadata
            evidence = Evidence(
                inspection_id=inspection.id,
                file_path=file_path
            )
            db.add(evidence)
            
            # 5. Commit transaction
            db.commit()
            
            return InspectionUploadResponse(
                inspection_id=inspection.id,
                product_id=product.id,
                status=inspection.status,
                image=ImageUploadResponse(
                    filename=filename,
                    content_type=content_type
                ),
                message="Product image uploaded successfully"
            )

        except Exception as e:
            db.rollback()
            # Clean up the file if DB fails to prevent orphans
            storage_service.delete_file(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create inspection record: {str(e)}"
            )

inspection_service = InspectionService()
