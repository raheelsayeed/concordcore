


class VariableEvaluationError(Exception):

    def __init__(self, errors, variable_id):

        msgs = "\n  ".join([str(e).replace("\n", "\n  ") for e in errors])
        message = "{}:\n  {}".format(variable_id or "{root}", msgs)

        super(VariableEvaluationError, self).__init__(message)

        self.errors = errors

        self.variable_id = variable_id



