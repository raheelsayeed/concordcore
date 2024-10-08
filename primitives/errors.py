import logging

log = logging.getLogger(__name__)

class ExpressionError(Exception):
    def __init__(self, expression, message):
        message =  message + f' expression={expression}'
        super(ExpressionError, self).__init__(message)
        
class ExpressionEvaluationError(ExpressionError):
    def __init__(self, expression, values,  message=None):
        msg = f'ExpressionEvaluationError for values={values} message={message}'
        super(ExpressionEvaluationError, self).__init__(expression, msg)

class ExpressionVariableNotFound(ExpressionError):
    def __init__(self, expression_var, expression):
        msg = f'var_id={expression_var} not found or undefined'
        super(ExpressionVariableNotFound, self).__init__(expression, msg)



class VarError(Exception):

    def __init__(self, message, variable_id):

        message =  message + f' variable_id={variable_id}'
        super(VarError, self).__init__(message)
        self.variable_id = variable_id
        log.error(f'{self.__class__}: {message}')



        
class VariableEvaluationError(Exception):

    def __init__(self, errors, variable_id):

        msgs = "\n  ".join([str(e).replace("\n", "\n  ") for e in errors])
        message = "{}:\n  {}".format(variable_id or "{root}", msgs)

       
        super(VariableEvaluationError, self).__init__(message)

        self.errors = errors

        self.variable_id = variable_id

        log.error(f'VariableEvaluationError variable_id={self.variable_id} error={message}')



