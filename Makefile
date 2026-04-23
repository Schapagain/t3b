.PHONY: backend frontend install

backend:
	cd backend && uvicorn api:app --reload --port 8000

frontend:
	cd frontend && npm run dev

install:
	cd backend && pip3 install -r requirements.txt
	cd frontend && npm install
