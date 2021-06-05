# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import List

import click

from lean.container import container
from lean.models.api import QCFullOrganization
from lean.models.products.base import Product, ProductDetails

_variables = {
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderAdjustedNetProductionOfFinishedMotorGasoline": "PET.WGFRPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfFinishedMotorGasoline": "PET.WGFSTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyProductSuppliedOfFinishedMotorGasoline": "PET.WGFUPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfCrudeOilInSpr": "PET.WCSSTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfDistillateFuelOilGreaterThan500PpmSulfur": "PET.WDGRPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfDistillateFuelOilGreaterThan500PpmSulfur": "PET.WDGSTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyExportsOfTotalDistillate": "PET.WDIEXUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfDistillateFuelOil": "PET.WDIIMUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfDistillateFuelOil": "PET.WDIRPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfKeroseneTypeJetFuel": "PET.WKJSTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyProductSuppliedOfKeroseneTypeJetFuel": "PET.WKJUPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfTotalGasoline": "PET.WGTIMUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfTotalGasoline": "PET.WGTSTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyGrossInputsIntoRefineries": "PET.WGIRIUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfReformulatedMotorGasoline": "PET.WGRIMUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfReformulatedMotorGasoline": "PET.WGRRPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfReformulatedMotorGasoline": "PET.WGRSTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfDistillateFuelOil": "PET.WDISTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyProductSuppliedOfDistillateFuelOil": "PET.WDIUPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfMilitaryKeroseneTypeJetFuel": "PET.WKMRPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyOperableCrudeOilDistillationCapacity": "PET.WOCLEUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyPropyleneNonfuelUseStocksAtBulkTerminals": "PET.WPLSTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfPropaneAndPropylene": "PET.WPRSTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyPercentUtilizationOfRefineryOperableCapacity": "PET.WPULEUS3.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyExportsOfResidualFuelOil": "PET.WREEXUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfResidualFuelOil": "PET.WREIMUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfCommercialKeroseneTypeJetFuel": "PET.WKCRPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyExportsOfKeroseneTypeJetFuel": "PET.WKJEXUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfKeroseneTypeJetFuel": "PET.WKJIMUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfKeroseneTypeJetFuel": "PET.WKJRPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksExcludingSprOfCrudeOil": "PET.WCESTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyExportsOfCrudeOil": "PET.WCREXUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyFieldProductionOfCrudeOil": "PET.WCRFPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfCrudeOil": "PET.WCRIMUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyNetImportsOfCrudeOil": "PET.WCRNTUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetInputOfCrudeOil": "PET.WCRRIUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfResidualFuelOil": "PET.WRERPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfResidualFuelOil": "PET.WRESTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyProductSuppliedOfResidualFuelOil": "PET.WREUPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyExportsOfTotalPetroleumProducts": "PET.WRPEXUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfTotalPetroleumProducts": "PET.WRPIMUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyNetImportsOfTotalPetroleumProducts": "PET.WRPNTUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyProductSuppliedOfPetroleumProducts": "PET.WRPUPUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksExcludingSprOfCrudeOilAndPetroleumProducts": "PET.WTESTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyExportsOfCrudeOilAndPetroleumProducts": "PET.WTTEXUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfCrudeOilAndPetroleumProducts": "PET.WTTIMUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyNetImportsOfCrudeOilAndPetroleumProducts": "PET.WTTNTUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfCrudeOilAndPetroleumProducts": "PET.WTTSTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfUnfinishedOils": "PET.WUOSTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfOtherFinishedConventionalMotorGasoline": "PET.WG6TP_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfDistillateFuelOil0To15PpmSulfur": "PET.WD0TP_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfDistillateFuelOilGreaterThan15To500PpmSulfur": "PET.WD1ST_NUS_1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyProductionOfDistillateFuelOilGreaterThan15To500PpmSulfur": "PET.WD1TP_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfReformulatedMotorGasolineWithFuelAlcohol": "PET.WG1ST_NUS_1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfCrudeOil": "PET.WCRSTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyCrudeOilImportsBySpr": "PET.WCSIMUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfGasolineBlendingComponents": "PET.WBCIMUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfGasolineBlendingComponents": "PET.WBCSTUS1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyCommercialCrudeOilImportsExcludingSpr": "PET.WCEIMUS2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerBlenderAndGasPlantNetProductionOfPropaneAndPropylene": "PET.WPRTP_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfFinishedReformulatedMotorGasolineWithEthanol": "PET.WG1TP_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfReformulatedMotorGasolineNonOxygentated": "PET.WG3ST_NUS_1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfConventionalMotorGasoline": "PET.WG4ST_NUS_1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfConventionalMotorGasoline": "PET.WG4TP_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfConventionalMotorGasolineWithFuelEthanol": "PET.WG5ST_NUS_1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfFinishedConventionalMotorGasolineWithEthanol": "PET.WG5TP_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfOtherConventionalMotorGasoline": "PET.WG6ST_NUS_1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetInputOfConventionalCbobGasolineBlendingComponents": "PET.WO6RI_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfConventionalCbobGasolineBlendingComponents": "PET.WO6ST_NUS_1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetInputOfConventionalGtabGasolineBlendingComponents": "PET.WO7RI_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfConventionalGtabGasolineBlendingComponents": "PET.WO7ST_NUS_1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetInputOfConventionalOtherGasolineBlendingComponents": "PET.WO9RI_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfConventionalOtherGasolineBlendingComponents": "PET.WO9ST_NUS_1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyNo2HeatingOilWholesaleResalePrice": "PET.W_EPD2F_PWR_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyCrudeOilStocksInTransitOnShipsFromAlaska": "PET.W_EPC0_SKA_NUS_MBBL.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyDaysOfSupplyOfCrudeOilExcludingSpr": "PET.W_EPC0_VSD_NUS_DAYS.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyDaysOfSupplyOfTotalDistillate": "PET.W_EPD0_VSD_NUS_DAYS.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyWeeklyNo2HeatingOilResidentialPrice": "PET.W_EPD2F_PRS_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyProductSuppliedOfPropaneAndPropylene": "PET.WPRUP_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyProductSuppliedOfOtherOils": "PET.WWOUP_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetInputOfGasolineBlendingComponents": "PET.WBCRI_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfDistillateFuelOil0To15PpmSulfur": "PET.WD0ST_NUS_1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyDaysOfSupplyOfKeroseneTypeJetFuel": "PET.W_EPJK_VSD_NUS_DAYS.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyDaysOfSupplyOfTotalGasoline": "PET.W_EPM0_VSD_NUS_DAYS.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfAsphaltAndRoadOil": "PET.W_EPPA_SAE_NUS_MBBL.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfKerosene": "PET.W_EPPK_SAE_NUS_MBBL.W",
    "USEnergy.Petroleum.UnitedStates.WeeklySupplyAdjustmentOfDistillateFuelOilGreaterThan15To500PpmSulfur": "PET.W_EPDM10_VUA_NUS_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfConventionalMotorGasolineWithFuelEthanol": "PET.WG5IM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfOtherConventionalMotorGasoline": "PET.WG6IM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfDistillateFuelOil0To15PpmSulfur": "PET.WD0IM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfDistillateFuelOilGreaterThan15To500PpmSulfur": "PET.WD1IM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfDistillateFuelOilGreaterThan500To2000PpmSulfur": "PET.WD2IM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfPropaneAndPropylene": "PET.WPRIM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfConventionalGtabGasolineBlendingComponents": "PET.WO7IM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfDistillateFuelOilGreaterThan2000PpmSulfur": "PET.WD3IM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfReformulatedMotorGasolineWithFuelAlcohol": "PET.WG1IM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfConventionalMotorGasoline": "PET.WG4IM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfConventionalOtherGasolineBlendingComponents": "PET.WO9IM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfConventionalCbobGasolineBlendingComponents": "PET.WO6IM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfKerosene": "PET.W_EPPK_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfKerosene": "PET.W_EPPK_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfOtherOilsExcludingFuelEthanol": "PET.W_EPPO6_SAE_NUS_MBBL.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfResidualFuelOil": "PET.W_EPPR_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfReformulatedMotorGasoline": "PET.W_EPM0R_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfReformulatedMotorGasoline": "PET.W_EPM0R_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfFuelEthanol": "PET.W_EPOOXE_SAE_NUS_MBBL.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfDistillateFuelOil": "PET.W_EPD0_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfDistillateFuelOil": "PET.W_EPD0_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfKeroseneTypeJetFuel": "PET.W_EPJK_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfKeroseneTypeJetFuel": "PET.W_EPJK_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyPropaneResidentialPrice": "PET.W_EPLLPA_PRS_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyPropaneWholesaleResalePrice": "PET.W_EPLLPA_PWR_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetInputOfMotorGasolineBlendingComponentsRbob": "PET.W_EPOBGRR_YIR_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfNgplsLrgsExcludingPropanePropylene": "PET.W_EPL0XP_SAE_NUS_MBBL.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyDaysOfSupplyOfPropanePropylene": "PET.W_EPLLPZ_VSD_NUS_DAYS.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfConventionalMotorGasoline": "PET.W_EPM0C_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfConventionalMotorGasoline": "PET.W_EPM0C_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklySupplyAdjustmentOfFinishedMotorGasoline": "PET.W_EPM0F_VUA_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfFinishedMotorGasoline": "PET.W_EPM0F_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfFinishedMotorGasoline": "PET.W_EPM0F_YPR_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfFinishedMotorGasoline": "PET.W_EPM0F_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfDistillateFuelOilGreaterThan500PpmSulfur": "PET.W_EPD00H_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfDistillateFuelOilGreaterThan500PpmSulfur": "PET.W_EPD00H_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfDistillateFuelOilGreaterThan15To500PpmSulfur": "PET.W_EPDM10_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfDistillateFuelOilGreaterThan15To500PpmSulfur": "PET.W_EPDM10_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfDistillateFuelOil0To15PpmSulfur": "PET.W_EPDXL0_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfDistillateFuelOil0To15PpmSulfur": "PET.W_EPDXL0_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfConventionalMotorGasolineWithFuelEthanol": "PET.W_EPM0CA_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfConventionalMotorGasolineWithFuelEthanol": "PET.W_EPM0CA_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfOtherConventionalMotorGasoline": "PET.W_EPM0CO_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfOtherConventionalMotorGasoline": "PET.W_EPM0CO_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfReformulatedMotorGasolineWithFuelAlcohol": "PET.W_EPM0RA_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfReformulatedMotorGasolineWithFuelAlcohol": "PET.W_EPM0RA_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyOxygenatePlantProductionOfFuelEthanol": "PET.W_EPOOXE_YOP_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfMotorGasolineFinishedConventionalEd55AndLower": "PET.W_EPM0CAL55_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfFinishedConventionalMotorGasolineEd55AndLower": "PET.W_EPM0CAL55_YPT_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfMotorGasolineFinishedConventionalEd55AndLower": "PET.W_EPM0CAL55_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyExportsOfFinishedMotorGasoline": "PET.W_EPM0F_EEX_NUS-Z00_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfFinishedMotorGasoline": "PET.W_EPM0F_IM0_NUS-Z00_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfOtherReformulatedMotorGasoline": "PET.W_EPM0RO_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfOtherFinishedReformulatedMotorGasoline": "PET.W_EPM0RO_YPT_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfOtherReformulatedMotorGasoline": "PET.W_EPM0RO_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfMotorGasolineBlendingComponentsRbob": "PET.W_EPOBGRR_SAE_NUS_MBBL.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetInputOfFuelEthanol": "PET.W_EPOOXE_YIR_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfMotorGasolineFinishedConventionalGreaterThanEd55": "PET.W_EPM0CAG55_IM0_NUS-Z00_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfMotorGasolineFinishedConventionalEd55AndLower": "PET.W_EPM0CAL55_IM0_NUS-Z00_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyCrudeOilImportsForSprByOthers": "PET.W_EPC0_IMU_NUS-Z00_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfConventionalMotorGasolineGreaterThanEd55": "PET.W_EPM0CAG55_SAE_NUS_MBBL.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfFuelEthanol": "PET.W_EPOOXE_IM0_NUS-Z00_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfLiquefiedPetroleumGassesLessPropanePropylene": "PET.W_EPL0XP_IM0_NUS-Z00_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyExportsOfPropaneAndPropylene": "PET.W_EPLLPZ_EEX_NUS-Z00_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfOtherReformulatedMotorGasoline": "PET.W_EPM0RO_IM0_NUS-Z00_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyBlenderNetProductionOfMotorGasolineFinishedConventionalGreaterThanEd55": "PET.W_EPM0CAG55_YPB_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerAndBlenderNetProductionOfFinishedConventionalMotorGasolineGreaterThanEd55": "PET.W_EPM0CAG55_YPT_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRefinerNetProductionOfFinishedConventionalMotorGasolineGreaterThanEd55": "PET.W_EPM0CAG55_YPY_NUS_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfConventionalMotorGasolineEd55AndLower": "PET.W_EPM0CAL55_SAE_NUS_MBBL.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfKerosene": "PET.W_EPPK_IM0_NUS-Z00_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyExportsOfOtherOils": "PET.W_EPPO4_EEX_NUS-Z00_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfOtherOilsExcludingFuelEthanol": "PET.W_EPPO6_IM0_NUS-Z00_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsFromAllCountriesOfMotorGasolineBlendingComponentsRbob": "PET.W_EPOBGRR_IM0_NUS-Z00_MBBLD.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRegularAllFormulationsRetailGasolinePrices": "PET.EMM_EPMR_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyMidgradeAllFormulationsRetailGasolinePrices": "PET.EMM_EPMM_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyPremiumAllFormulationsRetailGasolinePrices": "PET.EMM_EPMP_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyAllGradesAllFormulationsRetailGasolinePrices": "PET.EMM_EPM0_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyAllGradesReformulatedRetailGasolinePrices": "PET.EMM_EPM0R_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyMidgradeReformulatedRetailGasolinePrices": "PET.EMM_EPMMR_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyPremiumReformulatedRetailGasolinePrices": "PET.EMM_EPMPR_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRegularConventionalRetailGasolinePrices": "PET.EMM_EPMRU_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyRegularReformulatedRetailGasolinePrices": "PET.EMM_EPMRR_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyNo2DieselRetailPrices": "PET.EMD_EPD2D_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyPremiumConventionalRetailGasolinePrices": "PET.EMM_EPMPU_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyMidgradeConventionalRetailGasolinePrices": "PET.EMM_EPMMU_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyAllGradesConventionalRetailGasolinePrices": "PET.EMM_EPM0U_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyNo2DieselUltraLowSulfur015PpmRetailPrices": "PET.EMD_EPD2DXL0_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksExcludingSprAndIncludingLeaseStockOfCrudeOil": "PET.W_EPC0_SAX_NUS_MBBL.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyNo2DieselLowSulfur15500PpmRetailPrices": "PET.EMD_EPD2DM10_PTE_NUS_DPG.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfReformulatedRbobWithAlcoholGasolineBlendingComponents": "PET.WO3IM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyImportsOfReformulatedRbobWithEtherGasolineBlendingComponents": "PET.WO4IM_NUS-Z00_2.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfReformulatedGtabGasolineBlendingComponents": "PET.WO2ST_NUS_1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfReformulatedRbobWithAlcoholGasolineBlendingComponents": "PET.WO3ST_NUS_1.W",
    "USEnergy.Petroleum.UnitedStates.WeeklyEndingStocksOfReformulatedRbobWithEtherGasolineBlendingComponents": "PET.WO4ST_NUS_1.W",
    "USEnergy.Petroleum.EquatorialGuinea.WeeklyImportsFromEquatorialGuineaOfCrudeOil": "PET.W_EPC0_IM0_NUS-NEK_MBBLD.W",
    "USEnergy.Petroleum.Iraq.WeeklyImportsFromIraqOfCrudeOil": "PET.W_EPC0_IM0_NUS-NIZ_MBBLD.W",
    "USEnergy.Petroleum.Kuwait.WeeklyImportsFromKuwaitOfCrudeOil": "PET.W_EPC0_IM0_NUS-NKU_MBBLD.W",
    "USEnergy.Petroleum.Mexico.WeeklyImportsFromMexicoOfCrudeOil": "PET.W_EPC0_IM0_NUS-NMX_MBBLD.W",
    "USEnergy.Petroleum.Nigeria.WeeklyImportsFromNigeriaOfCrudeOil": "PET.W_EPC0_IM0_NUS-NNI_MBBLD.W",
    "USEnergy.Petroleum.Norway.WeeklyImportsFromNorwayOfCrudeOil": "PET.W_EPC0_IM0_NUS-NNO_MBBLD.W",
    "USEnergy.Petroleum.Russia.WeeklyImportsFromRussiaOfCrudeOil": "PET.W_EPC0_IM0_NUS-NRS_MBBLD.W",
    "USEnergy.Petroleum.SaudiArabia.WeeklyImportsFromSaudiArabiaOfCrudeOil": "PET.W_EPC0_IM0_NUS-NSA_MBBLD.W",
    "USEnergy.Petroleum.UnitedKingdom.WeeklyImportsFromUnitedKingdomOfCrudeOil": "PET.W_EPC0_IM0_NUS-NUK_MBBLD.W",
    "USEnergy.Petroleum.Venezuela.WeeklyImportsFromVenezuelaOfCrudeOil": "PET.W_EPC0_IM0_NUS-NVE_MBBLD.W",
    "USEnergy.Petroleum.Algeria.WeeklyImportsFromAlgeriaOfCrudeOil": "PET.W_EPC0_IM0_NUS-NAG_MBBLD.W",
    "USEnergy.Petroleum.Angola.WeeklyImportsFromAngolaOfCrudeOil": "PET.W_EPC0_IM0_NUS-NAO_MBBLD.W",
    "USEnergy.Petroleum.Brazil.WeeklyImportsFromBrazilOfCrudeOil": "PET.W_EPC0_IM0_NUS-NBR_MBBLD.W",
    "USEnergy.Petroleum.Canada.WeeklyImportsFromCanadaOfCrudeOil": "PET.W_EPC0_IM0_NUS-NCA_MBBLD.W",
    "USEnergy.Petroleum.Congo.WeeklyImportsFromCongoBrazzavilleOfCrudeOil": "PET.W_EPC0_IM0_NUS-NCF_MBBLD.W",
    "USEnergy.Petroleum.Colombia.WeeklyImportsFromColombiaOfCrudeOil": "PET.W_EPC0_IM0_NUS-NCO_MBBLD.W",
    "USEnergy.Petroleum.Ecuador.WeeklyImportsFromEcuadorOfCrudeOil": "PET.W_EPC0_IM0_NUS-NEC_MBBLD.W",
}


class USEnergyProduct(Product):
    """The USEnergyProduct class supports downloading US Energy data with the `lean data download` command."""

    def __init__(self, series_id: str) -> None:
        super().__init__()

        self._series_id = series_id

    @classmethod
    def get_product_name(cls) -> str:
        return "US Energy Information Administration Data"

    @classmethod
    def build(cls, organization: QCFullOrganization) -> List[Product]:
        logger = container.logger()
        logger.info(
            "See the available data at https://www.quantconnect.com/docs/alternative-data/us-energy-information-administration#US-Energy-Information-Administration-Petroleum-Datasets")
        logger.info("You can provide the id of the data in two different ways:")
        logger.info("1. Using the name of the variable passed to AddData(USEnergy, <variable>).")
        logger.info("   Example: USEnergy.Petroleum.UnitedStates.WeeklyImportsOfCrudeOil")
        logger.info("2. Using the series id used by the US Energy Information Administration.")
        logger.info("   Example: PET.WCRIMUS2.W")

        api_client = container.api_client()

        while True:
            given_data_id = click.prompt("Enter the id of the data")

            if given_data_id in _variables:
                data_id = _variables[given_data_id]
            else:
                data_id = given_data_id

            if len(api_client.data.list_files(f"alternative/usenergy/{data_id.lower()}.csv")) > 0:
                return [USEnergyProduct(data_id)]

            logger.info(f"Error: we have no data for {given_data_id}")

    def get_details(self) -> ProductDetails:
        return ProductDetails(data_type=self.get_product_name(),
                              ticker=self._series_id.upper(),
                              market="-",
                              resolution="Daily",
                              date_range="All available data")

    def _get_data_files(self) -> List[str]:
        return [f"alternative/usenergy/{self._series_id.lower()}.csv"]
