import hashlib
from .audit_models import AuditLog

def process_audit_event_task(payload):
    """
    Background worker task to process and save audit logs sequentially.
    Ensures that hash chaining is calculated without race conditions.
    """
    try:
        # Get the previous hash from the latest entry
        last_log = AuditLog.objects.order_by('-timestamp').first()
        previous_hash = last_log.current_hash if last_log and last_log.current_hash else "0000000000000000000000000000000000000000000000000000000000000000"

        # Prepare data for hashing
        hash_content = f"{previous_hash}|{payload.get('event_type')}|{payload.get('actor_id')}|{payload.get('resource_id')}"
        current_hash = hashlib.sha256(hash_content.encode('utf-8')).hexdigest()

        # Create record
        AuditLog.objects.create(
            event_type=payload.get('event_type'),
            severity_level=payload.get('severity_level', 'INFO'),
            actor_id=payload.get('actor_id'),
            actor_role=payload.get('actor_role', ''),
            ip_address=payload.get('ip_address'),
            user_agent=payload.get('user_agent', ''),
            resource_type=payload.get('resource_type', ''),
            resource_id=payload.get('resource_id', ''),
            before_state=payload.get('before_state', ''),
            after_state=payload.get('after_state', ''),
            status=payload.get('status', 'SUCCESS'),
            reason=payload.get('reason', ''),
            previous_hash=previous_hash,
            current_hash=current_hash
        )
    except Exception as e:
        # Safely catch error so worker doesn't crash on one failing log
        print(f"Error in process_audit_event_task: {e}")
