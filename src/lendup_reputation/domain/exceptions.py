class DomainError(Exception):
    """Base class for expected domain failures."""


class InvalidScoreError(DomainError):
    pass


class InvalidCommentError(DomainError):
    pass


class LoanNotFoundError(DomainError):
    pass


class LoanNotFinalizedError(DomainError):
    pass


class NotLoanParticipantError(DomainError):
    pass


class SelfRatingError(DomainError):
    pass


class DuplicateRatingError(DomainError):
    pass


class IdentityUnavailableError(DomainError):
    pass


class IdentityNotResolvedError(DomainError):
    pass


class AuthenticationError(DomainError):
    pass
