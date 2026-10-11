"""Enrolled attestation of the owned empty project; no genesis/store write."""
from claimbranch.core.canonical import ContractError, decode
from .mac_enrollment import enrollment_status
from .mac_review_signing import _sign_checked
from .project_initialization import ProjectInitialization


def sign_enrolled_initialization_review(runtime, expected_build, local_id, owner, review, *, current_context):
    """Reuse entered fields with live association rechecks and private signature."""
    if type(owner) is not ProjectInitialization or not callable(current_context):
        raise ContractError('owned initialization and current context reader required')

    def current():
        context = current_context()
        if type(context) is not dict or set(context) != {'session_nonce', 'now'}:
            raise ContractError('exact current initialization context required')
        try:
            candidate = owner.candidate(review, **context)
        except OSError:
            raise ContractError('initialization source check I/O failed; no project was accepted') from None
        return candidate.project.payload, candidate.association.payload

    before = current()
    try:
        enrollment = enrollment_status(runtime, expected_build, local_id)
    except OSError:
        raise ContractError('initialization enrollment I/O failed; no project was accepted') from None
    binding = enrollment['binding']
    if decode(review.payload)['seed']['project_id'] != binding['project_id']:
        raise ContractError('initialization belongs to another enrolled project')
    try:
        result = _sign_checked(runtime, expected_build, binding['key_directory'],
            binding['registration_digest'], review, enrollment=enrollment)
        after = enrollment_status(runtime, expected_build, local_id)
    except OSError:
        raise ContractError('initialization signing I/O failed; no project was accepted') from None
    if after != enrollment:
        raise ContractError('enrollment changed during initialization review')
    if result['status'] == 'signed-unaccepted-review' and current() != before:
        raise ContractError('initialization changed during native signing')
    return result
