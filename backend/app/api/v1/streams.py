from fastapi import APIRouter

from app.api.deps import EditorDep
from app.schemas.stream import AddOfferIn, SetShareIn, StreamOut

router = APIRouter(prefix="/streams/{stream_id}", tags=["stream editor"])


@router.get("", response_model=StreamOut)
async def get_stream(stream_id: int, editor: EditorDep) -> StreamOut:
    return StreamOut.from_model(await editor.get_stream(stream_id))


@router.post("/offers", response_model=StreamOut, summary="Add offer (draft) and rebalance shares")
async def add_offer(stream_id: int, data: AddOfferIn, editor: EditorDep) -> StreamOut:
    return StreamOut.from_model(await editor.add_offer(stream_id, data.offer_id))


@router.delete("/offers/{offer_id}", response_model=StreamOut, summary="Remove offer (draft) and rebalance")
async def remove_offer(stream_id: int, offer_id: int, editor: EditorDep) -> StreamOut:
    return StreamOut.from_model(await editor.remove_offer(stream_id, offer_id))


@router.post("/offers/{offer_id}/restore", response_model=StreamOut, summary="Bring a removed offer back")
async def restore_offer(stream_id: int, offer_id: int, editor: EditorDep) -> StreamOut:
    return StreamOut.from_model(await editor.restore_offer(stream_id, offer_id))


@router.patch("/offers/{offer_id}", response_model=StreamOut, summary="Pin share (int) or unpin (null)")
async def set_share(stream_id: int, offer_id: int, data: SetShareIn, editor: EditorDep) -> StreamOut:
    return StreamOut.from_model(await editor.set_share(stream_id, offer_id, data.share))


@router.post("/push", response_model=StreamOut, summary="Publish draft to Keitaro")
async def push(stream_id: int, editor: EditorDep) -> StreamOut:
    return StreamOut.from_model(await editor.push(stream_id))


@router.post("/cancel", response_model=StreamOut, summary="Discard draft, back to published state")
async def cancel(stream_id: int, editor: EditorDep) -> StreamOut:
    return StreamOut.from_model(await editor.cancel(stream_id))
