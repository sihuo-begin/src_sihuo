from src.libs.calibration.pathloss import PathlossTable
from src.libs.calibration.pathloss_calibration_controller import PathlossCalibrationController


def pathloss_calibration_step(connections, logger, **kwargs):
    controller = PathlossCalibrationController(
        connections=connections,
        logger=logger,
    )
    result = controller.pathloss_calibration(**kwargs)
    return result.ok, result.value
