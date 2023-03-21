import numpy as np
import torch
import warnings

# Internal imports
from physo.config.config0 import config0
import physo.learn.monitoring as monitoring
from physo.task.fit import fit

# DEFAULT RUN CONFIG TO USE
default_config = config0

# DEFAULT MONITORING CONFIG TO USE
default_run_logger     = monitoring.RunLogger(
                                      save_path = 'SR.log',
                                      do_save   = True)
default_run_visualiser = monitoring.RunVisualiser (
                                           epoch_refresh_rate = 1,
                                           save_path = 'SR_curves.png',
                                           do_show   = False,
                                           do_prints = True,
                                           do_save   = True, )

def SR(X, y,
       # X
       X_units = None,
       X_names = None,
       # y
       y_name  = None,
       y_units = None,
       # Fixed constants
       fixed_consts = None,
       fixed_consts_units = None,
       # Free constants
       free_consts_units  = None,
       free_consts_names  = None,
       # Operations to use
       op_names = None,
       # Stopping
       stop_reward = 0.9999,
       epochs = None,
       # Default run config to use
       run_config = default_config,
       # Default run monitoring
       run_logger     = default_run_logger,
       run_visualiser = default_run_visualiser,
       ):
    """
    Function to run a symbolic regression task using default hyperparameters.
    (Wrapper around physo.task.fit)
    Parameters
    ----------
    X
    y
    X_units
    X_names
    y_name
    y_units
    fixed_consts
    fixed_consts_units
    free_consts_units
    free_consts_names
    op_names
    stop_reward
    epochs
    run_config
    run_logger
    run_visualiser

    Returns
    -------

    """
    # --- DEVICE ---
    DEVICE = 'cpu'

    # ------------------------------- HANDLING ARGUMENTS -------------------------------

    # --- DATA ---
    X = np.array(X)
    y = np.array(y)
    # --- ASSERT FLOAT TYPE ---
    assert X.dtype == float, "X        must contain floats."
    assert y.dtype == float, "y_target must contain floats."
    assert np.isnan(X).any() == False, "X should not contain any Nans"
    assert np.isnan(y).any() == False, "y should not contain any Nans"
    # --- ASSERT SHAPE ---
    assert len(X.shape) == 2, "X        must have shape = (n_dim, data_size,)"
    assert len(y.shape) == 1, "y_target must have shape = (data_size,)"
    assert X.shape[1] == y.shape[0], "X must have shape = (n_dim, data_size,) and y_target must have " \
                                            "shape = (data_size,) with the same data_size."
    n_dim, data_size = X.shape

    # -- X_names --
    # Handling input variables names
    if X_names is None:
        # If None use x00, x01... names
        X_names = ["x%s"%(str(i).zfill(2)) for i in range(n_dim)]
    X_names = np.array(X_names)
    assert X_names.dtype.char == "U", "Input variables names should be strings."
    assert X_names.shape == (n_dim,), "There should be one input variable name per dimension in X."

    # -- X_units --
    # Handling input variables units
    if X_units is None:
        warnings.warn("No units given for input variables, assuming dimensionless units.")
        X_units = [[0,0,0] for _ in range(n_dim)]
    X_units = np.array(X_units).astype(float)
    assert X_units.shape[0] == n_dim, "There should be one input variable units per dimension in X."

    # --- y_name ---
    if y_name is None:
        y_name = "y"
    y_name = str(y_name)

    # --- y_units ---
    if y_units is None:
        warnings.warn("No units given for root variable, assuming dimensionless units.")
        y_units = [0,0,0]
    y_units = np.array(y_units).astype(float)
    assert len(y_units.shape) == 1, "y_units must be a 1D units vector"

    # --- n_fixed_consts ---
    if fixed_consts is not None:
        n_fixed_consts = len(fixed_consts)
    else:
        n_fixed_consts = 0
        fixed_consts = []
        warnings.warn("No information about fixed constants, not using any.")

    # --- fixed_consts_names ---
    fixed_consts_names = np.array([str(c) for c in fixed_consts])
    fixed_consts       = np.array(fixed_consts).astype(float)

    # --- fixed_consts_units ---
    if fixed_consts_units is None:
        warnings.warn("No units given for fixed constants, assuming dimensionless units.")
        fixed_consts_units = [[0,0,0] for _ in range(n_fixed_consts)]
    fixed_consts_units = np.array(fixed_consts_units).astype(float)
    assert fixed_consts_units.shape[0] == n_fixed_consts, "There should be one fixed constant units vector per fixed constant in fixed_consts_names"

    # --- n_free_consts ---
    if free_consts_names is not None:
        n_free_consts = len(free_consts_names)
    elif free_consts_units is not None:
        n_free_consts = len(free_consts_units)
    else:
        n_free_consts = 0
        warnings.warn("No information about free constants, not using any.")

    # --- free_consts_names ---
    if free_consts_names is None:
        # If None use c00, c01... names
        free_consts_names = ["c%s"%(str(i).zfill(2)) for i in range(n_free_consts)]
    free_consts_names = np.array(free_consts_names)
    assert free_consts_names.dtype.char == "U", "Free constants names should be strings."
    assert free_consts_names.shape == (n_free_consts,), "There should be one free constant name per units in free_consts_units"

    # --- free_consts_units ---
    if free_consts_units is None:
        warnings.warn("No units given for free constants, assuming dimensionless units.")
        free_consts_units = [[0,0,0] for _ in range(n_free_consts)]
    free_consts_units = np.array(free_consts_units).astype(float)
    assert free_consts_units.shape[0] == n_free_consts, "There should be one free constant units vector per free constant in free_consts_names"

    # --- op_names ---
    if op_names is None:
        op_names = ["mul", "add", "sub", "div", "inv", "n2", "sqrt", "neg", "exp", "log", "sin", "cos"]

    # ------------------------------- WRAPPING -------------------------------

    # Converting dataset to torch and sending to device
    X = torch.tensor(X).to(DEVICE)
    y = torch.tensor(y).to(DEVICE)
    fixed_consts = torch.tensor(fixed_consts).to(DEVICE)

    # Embedding wrapping
    args_make_tokens = {
                    # operations
                    "op_names"             : op_names,
                    "use_protected_ops"    : True,
                    # input variables
                    "input_var_ids"        : {X_names[i]: i          for i in range(n_dim)},
                    "input_var_units"      : {X_names[i]: X_units[i] for i in range(n_dim)},
                    # constants
                    "constants"            : {fixed_consts_names[i] : fixed_consts[i]       for i in range(n_fixed_consts)},
                    "constants_units"      : {fixed_consts_names[i] : fixed_consts_units[i] for i in range(n_fixed_consts)},
                    # free constants
                    "free_constants"       : {free_consts_names[i]                          for i in range(n_free_consts)},
                    "free_constants_units" : {free_consts_names[i] : free_consts_units[i]   for i in range(n_free_consts)},
                        }

    library_config = {"args_make_tokens"  : args_make_tokens,
                      "superparent_units" : y_units,
                      "superparent_name"  : y_name,
                    }

    # Monitoring
    run_config.update({
        "library_config"       : library_config,
        "run_logger"           : run_logger,
        "run_visualiser"       : run_visualiser,
    })

    # Number of epochs
    if epochs is not None:
        run_config["learning_config"]["n_epochs"] = epochs

    # ------------------------------- RUN -------------------------------

    print("SR task started...")
    rewards, candidates = fit (X, y, run_config,
                                stop_reward = stop_reward,
                                stop_after_n_epochs = 5)

    # ------------------------------- RESULTS -------------------------------

    pareto_front_complexities, pareto_front_programs, pareto_front_r, pareto_front_rmse = run_logger.get_pareto_front()
    best_prog = pareto_front_programs[-1]

    return best_prog, run_logger