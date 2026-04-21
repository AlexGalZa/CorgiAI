import { useState, useEffect } from 'react'
import { X, Loader2, AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'
import { useCreateOrganization, useUpdateOrganization, type OrganizationListItem } from '@/hooks/useOrganizations'
import Label from '@/components/ui/Label'
import { useFocusTrap } from '@/hooks/useFocusTrap'
import ConfirmDialog from '@/components/ui/ConfirmDialog'

interface OrganizationFormProps {
  organization?: OrganizationListItem | null
  open: boolean
  onClose: () => void
}

export default function OrganizationForm({ organization, open, onClose }: OrganizationFormProps) {
  const [name, setName] = useState('')
  const [isPersonal, setIsPersonal] = useState(false)
  const [showDeactivateConfirm, setShowDeactivateConfirm] = useState(false)

  const createMutation = useCreateOrganization()
  const updateMutation = useUpdateOrganization()

  const isEdit = !!organization

  useEffect(() => {
    if (organization) {
      setName(organization.name)
      setIsPersonal(organization.is_personal)
    } else {
      setName('')
      setIsPersonal(false)
    }
  }, [organization, open])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (open) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open, onClose])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      toast.error('Name is required')
      return
    }

    try {
      if (isEdit && organization) {
        await updateMutation.mutateAsync({ id: organization.id, name: name.trim(), is_personal: isPersonal })
        toast.success('Organization updated')
      } else {
        await createMutation.mutateAsync({ name: name.trim(), is_personal: isPersonal })
        toast.success('Organization created')
      }
      onClose()
    } catch {
      toast.error(isEdit ? 'Failed to update organization' : 'Failed to create organization')
    }
  }

  const focusTrapRef = useFocusTrap(open)

  if (!open) return null

  const isPending = createMutation.isPending || updateMutation.isPending

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/20 animate-in fade-in duration-150" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div ref={focusTrapRef} className="w-full max-w-md rounded-xl border border-gray-200 bg-white shadow-xl animate-in fade-in zoom-in-95 duration-150">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900">
              {isEdit ? 'Edit Organization' : 'New Organization'}
            </h2>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4 p-6">
            <div>
              <Label required>Name</Label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Organization name"
                autoFocus
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 transition-colors focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
              />
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setIsPersonal(!isPersonal)}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[#ff5c00] focus:ring-offset-2 ${
                  isPersonal ? 'bg-[#ff5c00]' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    isPersonal ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
              <Label className="mb-0">Personal Organization</Label>
            </div>

            {/* Deactivation warning - edit mode only */}
            {isEdit && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                <div className="flex gap-3">
                  <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
                  <div>
                    <h4 className="text-sm font-semibold text-red-800">Deactivate Organization</h4>
                    <p className="mt-1 text-sm text-red-700">
                      Removing this organization will set its status to inactive and disassociate all members. Active policies under this organization will need to be reassigned or cancelled separately.
                    </p>
                    <button
                      type="button"
                      onClick={() => setShowDeactivateConfirm(true)}
                      className="mt-3 rounded-lg border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-50"
                    >
                      Deactivate Organization
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPending || !name.trim()}
                className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#ea580c] disabled:opacity-50"
              >
                {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                {isEdit ? 'Update' : 'Create'}
              </button>
            </div>
          </form>
        </div>
      </div>

      <ConfirmDialog
        open={showDeactivateConfirm}
        title="Deactivate Organization"
        message="This will set the organization to inactive and disassociate all members. Active policies will need to be reassigned or cancelled separately. Are you sure you want to proceed?"
        confirmLabel="Deactivate"
        variant="danger"
        onConfirm={async () => {
          if (organization) {
            try {
              await updateMutation.mutateAsync({ id: organization.id, name: organization.name, is_personal: false })
              toast.success('Organization deactivated')
              setShowDeactivateConfirm(false)
              onClose()
            } catch {
              toast.error('Failed to deactivate organization')
            }
          }
        }}
        onCancel={() => setShowDeactivateConfirm(false)}
      />
    </>
  )
}
