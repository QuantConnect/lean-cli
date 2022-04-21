import click
import abc
from lean.components.util.logger import Logger

class Configuration(abc.ABC):
    def __init__(self, config_json_object):
        self._name = config_json_object["Name"]
        self._config_type = config_json_object["Type"]
        self._value = config_json_object["Value"]
        self._envrionment = config_json_object["Environment"]
        self._is_type_configurations_env = type(self) is ConfigurationsEnvConfiguration
        self._is_type_brokerage_env = type(self) is BrokerageEnvConfiguration

    @abc.abstractmethod
    def is_required_from_user(self):
        return NotImplemented()

    def factory(config_json_object):
        if config_json_object["Type"] in ["info" , "configurations-env"] :
            return InfoConfiguration.factory(config_json_object)
        elif config_json_object["Type"] == "input":
            return UserInputConfiguration.factory(config_json_object)
        elif config_json_object["Type"] == "brokerage-env":
            return BrokerageEnvConfiguration(config_json_object)

class InfoConfiguration(Configuration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    def factory(config_json_object):
        if config_json_object["Type"] == "configurations-env":
            return ConfigurationsEnvConfiguration(config_json_object)
        else:
            return InfoConfiguration(config_json_object)

    def is_required_from_user(self):
        return False
 
class ConfigurationsEnvConfiguration(InfoConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        self._env_and_values = {env_obj["Name"]:env_obj["Value"] for env_obj in self._value}

class UserInputConfiguration(Configuration, abc.ABC):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        self._input_method = config_json_object["Input-method"]
        self._input_type = config_json_object["Input-type"]
        self._input_data = config_json_object["Input-data"]
        self._help = config_json_object["Help"]

    @abc.abstractmethod
    def AskUserForInput(self, default_value):
        return NotImplemented()

    def factory(config_json_object):
        if config_json_object["Input-method"] == "prompt":
            return PromptUserInput(config_json_object)
        elif config_json_object["Input-method"] == "choice":
            return ChoiceUserInput(config_json_object)
        elif config_json_object["Input-method"] == "confirm":
            return ConfirmUserInput(config_json_object)
        elif config_json_object["Input-method"] == "prompt-password":
            return PromptPasswordUserInput(config_json_object)

    def is_required_from_user(self):
        return True

class PromptUserInput(UserInputConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    def AskUserForInput(self, default_value, logger: Logger):
        return click.prompt(self._input_data, default_value)

class ChoiceUserInput(UserInputConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        if "Input-choices" in config_json_object.keys():
            self._choices = config_json_object["Input-choices"]
        else:
            self._choices = []

    def AskUserForInput(self, default_value, logger: Logger):
        return click.prompt(
                    self._input_data,
                    default_value,
                    type=click.Choice(self._choices, case_sensitive=False)
                )

class ConfirmUserInput(UserInputConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    def AskUserForInput(self, default_value, logger: Logger):
        return click.confirm(self._input_data)

class PromptPasswordUserInput(UserInputConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    def AskUserForInput(self, default_value, logger: Logger):
        return logger.prompt_password(self._input_data, default_value)

class BrokerageEnvConfiguration(PromptUserInput, ChoiceUserInput, ConfirmUserInput):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    @property
    def _is_paper_environment(self):
        if self._input_method == "confirm":
            return self._value
        elif self._input_method == "choice":
            return True if self._value in ["Practice", "Paper"] else False
        elif self._input_method == "prompt":
            return True if self._value in ["Practice", "Paper"] else False
        else:
            raise(f"Undefined input method type {self._input_method}")
            
    def AskUserForInput(self, default_value, logger: Logger):
        if self._input_method == "confirm":
            return ConfirmUserInput.AskUserForInput(self, default_value, logger)
        elif self._input_method == "choice":
            return ChoiceUserInput.AskUserForInput(self, default_value, logger)
        elif self._input_method == "prompt":
            return PromptUserInput.AskUserForInput(self, default_value, logger)
        else:
            raise(f"Undefined input method type {self._input_method}")