:py:mod:`steelscript.netprofiler.core`
======================================

All interaction with a NetProfiler requires an instance of
:py:class:`NetProfiler <steelscript.netprofiler.core.Netprofiler>` This class
establishes a connection to the NetProfiler.

If you are new to SteelScript for NetProfiler, see the :doc:`Tutorial
<tutorial>`.

.. automodule:: steelscript.netprofiler.core

.. currentmodule:: steelscript.netprofiler.core.netprofiler

:py:class:`NetProfiler` objects
-------------------------------

.. autoclass:: NetProfiler
   :members:

   .. automethod:: __init__

.. currentmodule:: steelscript.netprofiler.core.report

:py:class:`Report` objects
---------------------------

.. autoclass:: Report
   :members:

   .. automethod:: __init__

:py:class:`SingleQueryReport` objects
-------------------------------------

.. autoclass:: SingleQueryReport
   :members:
   :show-inheritance:

   .. automethod:: __init__

:py:class:`TrafficSummaryReport`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: TrafficSummaryReport
   :members:
   :inherited-members:
   :show-inheritance:

   .. automethod:: __init__

:py:class:`TrafficOverallTimeSeriesReport`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: TrafficOverallTimeSeriesReport
   :members:
   :inherited-members:
   :show-inheritance:

   .. automethod:: __init__

:py:class:`TrafficFlowListReport`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: TrafficFlowListReport
   :members:
   :inherited-members:
   :show-inheritance:

   .. automethod:: __init__

:py:class:`IdentityReport`
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: IdentityReport
   :members:
   :inherited-members:
   :show-inheritance:

   .. automethod:: __init__

:py:class:`WANSummaryReport`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: WANSummaryReport
   :members:
   :inherited-members:

   .. automethod:: __init__

:py:class:`WANTimeSeriesReport`
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: WANTimeSeriesReport
   :members:
   :inherited-members:

   .. automethod:: __init__

:py:class:`MultiQueryReport` objects
-------------------------------------

.. autoclass:: MultiQueryReport
   :members:
   :show-inheritance:

   .. automethod:: __init__

:py:mod:`steelscript.netprofiler.core.filters`
==============================================

.. automodule:: steelscript.netprofiler.core.filters

.. currentmodule:: steelscript.netprofiler.core.filters

:py:class:`TimeFilter`
--------------------------

.. autoclass:: TimeFilter
   :members:

   .. automethod:: __init__

:py:class:`TrafficFilter`
--------------------------

.. autoclass:: TrafficFilter
   :members:

   .. automethod:: __init__
