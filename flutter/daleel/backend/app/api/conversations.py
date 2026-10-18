from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from .. import schemas as s
from ..services import conversation as svc
from .deps import get_db

router = APIRouter(prefix="/api/conversations", tags=["Sandbox conversation"])


@router.get("", response_model=list[s.ConversationOut])
def list_conversations(lead_id: int = Query(...), db: Session = Depends(get_db)):
    return [svc._out(c) for c in svc.list_for_lead(db, lead_id)]


@router.post("", response_model=s.ConversationOut, status_code=201)
def open_conversation(body: s.ConversationCreate, request: Request, db: Session = Depends(get_db)):
    conv = svc.open_conversation(db, body.lead_id, body.channel, request.app.state.registry)
    return svc._out(conv)


@router.get("/{conversation_id}", response_model=s.ConversationOut)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    return svc._out(svc.get_conversation(db, conversation_id))


@router.post("/{conversation_id}/messages", response_model=s.ConversationOut)
def post_message(conversation_id: int, body: s.ChatMessageIn, request: Request, db: Session = Depends(get_db)):
    conv = svc.post_message(db, conversation_id, body.text, request.app.state.registry)
    return svc._out(conv)
