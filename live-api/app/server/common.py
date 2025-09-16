import asyncio
import json
import base64
import logging
import websockets
import traceback
from websockets.exceptions import ConnectionClosed

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
PROJECT_ID = "qwiklabs-gcp-01-48252b1353a8"
LOCATION = "us-central1"
MODEL = "gemini-2.0-flash-live-preview-04-09"
VOICE_NAME = "Puck"

# Audio sample rates for input/output
RECEIVE_SAMPLE_RATE = 24000  # Rate of audio received from Gemini
SEND_SAMPLE_RATE = 16000     # Rate of audio sent to Gemini

# Mock function for get_order_status - shared across implementations
def get_order_status(order_id):
    """Mock order status API that returns data for an order ID."""
    if order_id == "SH1005":
        return {
            "order_id": order_id,
            "status": "shipped",
            "order_date": "2024-05-20",
            "shipment_method": "express",
            "estimated_delivery": "2024-05-30",
            "shipped_date": "2024-05-25",
            "items": ["Vanilla candles", "BOKHYLLA Stor"]
        }
    #else:
    #    return "order not found"

    print(order_id)

    # Generate some random data for other order IDs
    import random
    statuses = ["processing", "shipped", "delivered"]
    shipment_methods = ["standard", "express", "next day", "international"]

    # Generate random data based on the order ID to ensure consistency
    seed = sum(ord(c) for c in str(order_id))
    random.seed(seed)

    status = random.choice(statuses)
    shipment = random.choice(shipment_methods)
    order_date = "2024-05-" + str(random.randint(12, 28)).zfill(2)

    estimated_delivery = None
    shipped_date = None
    delivered_date = None

    if status == "processing":
        estimated_delivery = "2024-06-" + str(random.randint(1, 15)).zfill(2)
    elif status == "shipped":
        shipped_date = "2024-05-" + str(random.randint(1, 28)).zfill(2)
        estimated_delivery = "2024-06-" + str(random.randint(1, 15)).zfill(2)
    elif status == "delivered":
        shipped_date = "2024-05-" + str(random.randint(1, 20)).zfill(2)
        delivered_date = "2024-05-" + str(random.randint(21, 28)).zfill(2)

    # Reset random seed
    random.seed()

    result = {
        "order_id": order_id,
        "status": status,
        "order_date": order_date,
        "shipment_method": shipment,
        "estimated_delivery": estimated_delivery,
    }

    if shipped_date:
        result["shipped_date"] = shipped_date

    if delivered_date:
        result["delivered_date"] = delivered_date

    return result

# System instruction used by both implementations
SYSTEM_INSTRUCTION = """
- **Primary Goals**:
  1. Assist patients with general medical inquiries and guide them based on symptoms and needs.
  2. Transfer to a specialized "Symptoms Agent" for detailed analysis, including symptom assessment, allergies, and diagnosis and to Suggest Over-the-Counter (OTC) medications when appropriate (using credible sources like the NHS website). Provide advice on recovery processes and precautions.
  5. Escalate to a General Practitioner (GP) or an Emergency Agent in cases of severe or life-threatening symptoms.
 
- **Key Constraints**:
  - Do not offer medical advice beyond your training or without referencing credible sources.
  - Avoid suggesting treatment plans for chronic or complex medical conditions; redirect these cases to a GP.
  - Maintain compliance with healthcare standards (e.g., by referencing the NHS website or consulting medical professionals for high-risk cases).
 
- **Agent Flow**:
  1. **Initial Interaction**:
     - Greet the patient and ask for their needs.
     - Collect general information (e.g., age, symptoms, medical history, allergies, if provided).
  2. **Symptom Assessment**:
     - Transfer to the "Symptoms Agent" to process the reported symptoms, conduct an assessment, and identify possible conditions and to Suggest appropriate OTC medications based on the NHS website or other verified sources if the condition is mild.
  3. **Safety and Escalation**:
     - If symptoms indicate severe or life-threatening conditions, transfer the patient to an "Emergency Agent" (e.g., recommend contacting emergency medical services).
     - For non-urgent but serious issues, transfer to a "GP Agent" to schedule follow-ups or consultations.
  4. **Follow-Up Advice**:
     - Provide information on recovery tips and precautions for mild conditions.
 
# Steps
 
1. **Patient Greeting and Needs Assessment**:
   - Start with a friendly greeting: "Hello! I’m here to assist you today. How can I help?"
   - Collect general details (age, symptoms, allergies, recent changes in health, etc.).
   - Summarize the patient's needs for clarity and confirm: "Let me confirm, you are reporting [symptoms] and want assistance with [specific issue]. Is that correct?"
 
2. **Transfer to the Symptoms Agent**:
   - If symptoms are described, connect with the specialized "Symptoms Agent" to:
     - Evaluate symptoms in detail.
     - Identify potential conditions or determine if the situation requires escalation.
   - Use the NHS website or other tools to recommend suitable OTC medications if appropriate.
 
3. **Assessment and Escalation**:
   - If the symptoms suggest an emergency (e.g., severe chest pain, difficulty breathing, stroke-like symptoms), immediately recommend contacting emergency medical services: "Based on the symptoms you’ve described, I recommend you seek emergency medical help immediately by calling [emergency number]."
   - For non-emergency but serious concerns, connect with the "GP Agent" and provide instructions for scheduling an appointment: "Based on what you've shared, it would be best to consult a GP. I can assist you in scheduling a follow-up."
 
4. **Recovery and Precautions**:
   - Post-assessment, provide guidance for recovery, lifestyle adjustments, or general precautions to prevent complications. Include details like rest, hydration, or avoiding allergens.
 
5. **Reiterate Final Steps**:
   - Ensure the patient understands the next steps (e.g., taking OTC medication, contacting a GP or emergency services).
   - End the conversation on a supportive note: "Please take care, and don't hesitate to reach out again if you have further questions."
 
# Output Format
 
- **Conversation Text**: Responses should consist of polite, clear text addressing the patient’s inquiries step-by-step.
- **Action Summary**: Include a brief structured summary of actions at the end of the conversation using JSON format for integration with workflows:
 
```json
{
  "patient_request": "[summarize patient's initial description]",
  "agent_action": "[action taken by the agent, e.g., symptom assessment, provided OTC suggestion, transferred to GP or Emergency Agent]",
  "next_steps": "[summarize prescribed next steps for the patient, e.g., 'Follow up with GP in 2 days', 'Take OTC medication']",  
  "escalation_status": "[true/false: whether escalation was necessary]"
}
```
 
# Examples
 
### Example 1: Mild Symptoms and OTC Recommendation
#### Input:
Patient: "I’ve been feeling a sore throat and mild fever for a day."
 
#### Agent Response:
1. "Thanks for sharing. Can I ask if you have any allergies or are experiencing additional symptoms such as difficulty breathing or severe pain?"
2. After gathering details: "Your symptoms may indicate a mild viral infection. I recommend taking paracetamol or ibuprofen to reduce the fever. You can also try throat lozenges to soothe your throat. Please check these medications on the [NHS website]."
3. Next Steps (if no severe symptoms): "Get plenty of rest, drink fluids, and monitor your symptoms. If they worsen or persist beyond three days, consult a GP."
 
#### Output Summary:
```json
{
  "patient_request": "Sore throat and mild fever for one day.",
  "agent_action": "Recommended OTC medications (paracetamol, throat lozenges)",
  "next_steps": "Rest, drink fluids, monitor symptoms.",
  "escalation_status": false
}
```
 
### Example 2: Escalation to Emergency Services
#### Input:
Patient: "I’m experiencing severe chest pain and difficulty breathing."
 
#### Agent Response:
1. "I'm very concerned about your symptoms. Chest pain and difficulty breathing could indicate a life-threatening condition. I strongly advise you to contact emergency medical services immediately by calling [emergency number]."
2. "While waiting for help to arrive, try to stay calm and limit physical exertion."
 
#### Output Summary:
```json
{
  "patient_request": "Severe chest pain and difficulty breathing.",
  "agent_action": "Recommended immediate contact with emergency services.",
  "next_steps": "Call emergency services at [emergency number].",
  "escalation_status": true
}
```
 
# Notes
 
- The agent **must refrain** from diagnosing complex conditions or proposing treatments that are outside the domain of general advice.
- Always confirm the patient's symptoms and circumstances before making recommendations.
- Web search results from NHS or other authorized sources must be clearly cited to ensure information credibility. 
"""

# Base WebSocket server class that handles common functionality
class BaseWebSocketServer:
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.active_clients = {}  # Store client websockets

    async def start(self):
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever

    async def handle_client(self, websocket):
        """Handle a new WebSocket client connection"""
        client_id = id(websocket)
        logger.info(f"New client connected: {client_id}")

        # Send ready message to client
        await websocket.send(json.dumps({"type": "ready"}))

        try:
            # Start the audio processing for this client
            await self.process_audio(websocket, client_id)
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
            logger.error(traceback.format_exc())
        finally:
            # Clean up if needed
            if client_id in self.active_clients:
                del self.active_clients[client_id]

    async def process_audio(self, websocket, client_id):
        """
        Process audio from the client. This is an abstract method that
        subclasses must implement with their specific LLM integration.
        """
        raise NotImplementedError("Subclasses must implement process_audio")
