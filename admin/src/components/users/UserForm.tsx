import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { toast } from 'sonner'
import { useCreateUser, useUpdateUser } from '@/hooks/useUsers'
import { usePermissions } from '@/lib/permissions'
import type { User } from '@/types'
import Spinner from '@/components/ui/Spinner'
import Checkbox from '@/components/ui/Checkbox'
import Select from '@/components/ui/Select'
import Label from '@/components/ui/Label'
import { useFocusTrap } from '@/hooks/useFocusTrap'

const ROLE_OPTIONS = [
  { value: 'bdr', label: 'BDR' },
  { value: 'ae', label: 'Account Executive' },
  { value: 'ae_underwriting', label: 'AE + Underwriting' },
  { value: 'finance', label: 'Finance' },
  { value: 'broker', label: 'Broker' },
  { value: 'admin', label: 'Admin' },
]

interface UserFormProps {
  user?: User
  onClose: () => void
  onSaved: () => void
}

export default function UserForm({ user, onClose, onSaved }: UserFormProps) {
  const isEditing = !!user
  const createMutation = useCreateUser()
  const updateMutation = useUpdateUser()
  const focusTrapRef = useFocusTrap(true)
  const { canAssignPermissions } = usePermissions()

  const [form, setForm] = useState({
    email: '',
    first_name: '',
    last_name: '',
    phone_number: '',
    company_name: '',
    role: 'ae',
    is_active: true,
    password: '',
  })

  const [error, setError] = useState('')

  useEffect(() => {
    if (user) {
      setForm({
        email: user.email,
        first_name: user.first_name,
        last_name: user.last_name,
        phone_number: user.phone_number || '',
        company_name: user.company_name || '',
        role: user.role,
        is_active: user.is_active,
        password: '',
      })
    }
  }, [user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    try {
      if (isEditing && user) {
        const { password, ...payload } = form
        await updateMutation.mutateAsync({ id: user.id, payload })
        toast.success('User updated successfully')
      } else {
        if (!form.password) {
          setError('Password is required for new users')
          return
        }
        await createMutation.mutateAsync(form)
        toast.success('User created successfully')
      }
      onSaved()
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? JSON.stringify((err as { response: { data: unknown } }).response.data)
          : 'An error occurred'
      setError(msg)
      toast.error('Failed to save user')
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  const inputClass =
    'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 animate-in fade-in duration-150">
      <div ref={focusTrapRef} className="w-full max-w-lg rounded-xl border border-gray-200 bg-white shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {isEditing ? 'Edit User' : 'New User'}
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
        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
          {error && (
            <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label required>First Name</Label>
              <input
                type="text"
                value={form.first_name}
                onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
                className={inputClass}
                required
                autoFocus={!!user}
              />
            </div>
            <div>
              <Label required>Last Name</Label>
              <input
                type="text"
                value={form.last_name}
                onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
                className={inputClass}
                required
              />
            </div>
          </div>

          <div>
            <Label required>Email</Label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              className={inputClass}
              required
              autoFocus={!user}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Phone Number</Label>
              <input
                type="text"
                value={form.phone_number}
                onChange={(e) => setForm((f) => ({ ...f, phone_number: e.target.value }))}
                className={inputClass}
              />
            </div>
            <div>
              <Label>Company Name</Label>
              <input
                type="text"
                value={form.company_name}
                onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
                className={inputClass}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {canAssignPermissions && (
              <div>
                <Label>Role</Label>
                <Select
                  value={form.role}
                  onChange={(val) => setForm((f) => ({ ...f, role: val }))}
                  options={ROLE_OPTIONS}
                />
              </div>
            )}
            <div className="flex items-end pb-1">
              <Checkbox
                checked={form.is_active}
                onChange={(v) => setForm((f) => ({ ...f, is_active: v }))}
                label="Active"
              />
            </div>
          </div>

          {!isEditing && (
            <div>
              <Label required>Password</Label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                className={inputClass}
                required
                minLength={8}
              />
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#ea580c] disabled:opacity-50"
            >
              {isPending && <Spinner size="sm" />}
              {isEditing ? 'Save Changes' : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
