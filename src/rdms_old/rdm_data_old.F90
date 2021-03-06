module rdm_data_old

    ! Module containing global data and derived types used for RDM calculation.

    use constants, only: dp
    use rdm_data, only: one_rdm_t

    implicit none

    ! This is an old option which isn't great, because it determines whether
    ! or not the RDM energy is calculated, but is also used to determine
    ! whether or not an RDMEstimates file is opened at all - if not then other
    ! estimates won't be output to it either, and the code may crash if this is
    ! attempted.
    !logical :: tCalc_RDMEnergy

    ! Arrays used as storage when summing RDMs over all processors.
    real(dp), allocatable :: AllNodes_RDM_small(:,:), AllNodes_RDM_large(:,:)

    ! Unit of the separate file to which RDM estimates (such as energy and
    ! spin^2) are output - for *old* RDM accumulation only.
    integer :: rdm_write_unit_old

    ! Derived type to hold data for each RDM.

    type rdm_t
        ! Arrays to hold instantaneous estimates of 2-RDMs.
        ! The following three arrays are always used.
        real(dp), pointer :: aaaa_inst(:,:) => null(), abab_inst(:,:) => null(), abba_inst(:,:) => null()
        ! And the following three arrays are only used for open shell calculations
        ! (and possibly UHF systems in the future?).
        real(dp), pointer :: bbbb_inst(:,:) => null(), baba_inst(:,:) => null(), baab_inst(:,:) => null()

        ! Arrays to hold estimates of 2-RDMs, summed over the whole RDM calculation.
        real(dp), pointer :: aaaa_full(:,:) => null(), abab_full(:,:) => null(), abba_full(:,:) => null()
        real(dp), pointer :: bbbb_full(:,:) => null(), baba_full(:,:) => null(), baab_full(:,:) => null()

        ! Tags for the memory manager for the above RDM arrays.
        integer :: aaaa_instTag, abab_instTag, abba_instTag
        integer :: bbbb_instTag, baba_instTag, baab_instTag
        integer :: aaaa_fullTag, abab_fullTag, abba_fullTag
        integer :: bbbb_fullTag, baba_fullTag, baab_fullTag

        ! Pointers which can point to *_inst or *_full, depending on what the user
        ! has asked for.
        real(dp), pointer :: aaaa(:,:) => null()
        real(dp), pointer :: abab(:,:) => null()
        real(dp), pointer :: abba(:,:) => null()
        real(dp), pointer :: bbbb(:,:) => null()
        real(dp), pointer :: baba(:,:) => null()
        real(dp), pointer :: baab(:,:) => null()
    end type rdm_t

    type rdm_estimates_old_t
        real(dp) :: RDMEnergy, RDMEnergy1, RDMEnergy2, RDMEnergy_Inst
        real(dp) :: Norm_2RDM, Norm_2RDM_Inst, Trace_2RDM, Trace_2RDM_normalised
        real(dp) :: spin_est
    end type rdm_estimates_old_t

    ! Array of type rdm_t, for holding multiple different RDM instances.
    type(one_rdm_t), allocatable :: one_rdms_old(:)
    type(rdm_t), allocatable :: rdms(:)
    type(rdm_estimates_old_t), allocatable :: rdm_estimates_old(:)

end module rdm_data_old
