import { useState } from 'react'
import { useAuthStore } from '@/stores/auth'
import { toast } from 'sonner'
import { User, Mail, Shield, Phone, Building2, Lock, Loader2 } from 'lucide-react'
import PageHeader from '@/components/ui/PageHeader'
import Label from '@/components/ui/Label'
import { cn } from '@/lib/utils'
import api from '@/lib/api'

function formatRole(role: string): string {
  return role
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

const roleBadgeColors: Record<string, string> = {
  admin: 'bg-red-600',
  broker: 'bg-emerald-600',
  finance: 'bg-amber-500',
  account_executive: 'bg-sky-600',
  customer_support: 'bg-purple-600',
  account_manager: 'bg-violet-600',
}

async function changePassword(currentPassword: string, newPassword: string) {
  const { data } = await api.post('/users/me', {
    current_password: currentPassword,
    new_password: newPassword,
  })
  return data
}

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user)
  const [firstName, setFirstName] = useState(user?.first_name ?? '')
  const [lastName, setLastName] = useState(user?.last_name ?? '')
  const [phoneNumber, setPhoneNumber] = useState(user?.phone_number ?? '')
  const [companyName, setCompanyName] = useState(user?.company_name ?? '')
  const [saving, setSaving] = useState(false)

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [changingPassword, setChangingPassword] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      const { data } = await api.patch('/users/me', {
        first_name: firstName,
        last_name: lastName,
        phone_number: phoneNumber,
        company_name: companyName,
      })
      // Update the store directly
      useAuthStore.setState({ user: data })
      toast.success('Profile updated')
    } catch {
      toast.error('Failed to update profile')
    } finally {
      setSaving(false)
    }
  }

  const handlePasswordChange = async () => {
    if (!currentPassword || !newPassword) {
      toast.error('Please fill in all password fields')
      return
    }
    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match')
      return
    }
    if (newPassword.length < 8) {
      toast.error('New password must be at least 8 characters')
      return
    }

    setChangingPassword(true)
    try {
      await changePassword(currentPassword, newPassword)
      toast.success('Password changed successfully')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      const message = error?.response?.data?.detail || 'Failed to change password'
      toast.error(message)
    } finally {
      setChangingPassword(false)
    }
  }

  if (!user) return null

  const initials = `${user.first_name?.[0] ?? ''}${user.last_name?.[0] ?? ''}`.toUpperCase()

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader title="Profile" subtitle="Manage your account settings" />

      {/* Avatar + role */}
      <div className="flex items-center gap-5 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className={cn('flex h-16 w-16 items-center justify-center rounded-full text-xl font-bold text-white', roleBadgeColors[user.role] ?? 'bg-gray-500')}>
          {initials || '?'}
        </div>
        <div>
          <p className="text-lg font-semibold text-gray-900">{user.full_name}</p>
          <p className="text-sm text-gray-500">{user.email}</p>
          <span className={cn('mt-1 inline-block rounded-full px-2.5 py-0.5 text-xs font-medium text-white', roleBadgeColors[user.role] ?? 'bg-gray-500')}>
            {formatRole(user.role)}
          </span>
        </div>
      </div>

      {/* Edit form */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-sm font-semibold text-gray-900">Personal Information</h3>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>First Name</Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 py-2 pl-10 pr-3 text-sm text-gray-900 transition-colors focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
                />
              </div>
            </div>
            <div>
              <Label>Last Name</Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 py-2 pl-10 pr-3 text-sm text-gray-900 transition-colors focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
                />
              </div>
            </div>
          </div>

          <div>
            <Label>Phone Number</Label>
            <div className="relative">
              <Phone className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="(555) 123-4567"
                className="w-full rounded-lg border border-gray-200 py-2 pl-10 pr-3 text-sm text-gray-900 transition-colors focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
              />
            </div>
          </div>

          <div>
            <Label>Company Name</Label>
            <div className="relative">
              <Building2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="Your company"
                className="w-full rounded-lg border border-gray-200 py-2 pl-10 pr-3 text-sm text-gray-900 transition-colors focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
              />
            </div>
          </div>

          {/* Read-only fields */}
          <div>
            <Label>Email</Label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={user.email}
                disabled
                className="w-full rounded-lg border border-gray-100 bg-gray-50 py-2 pl-10 pr-3 text-sm text-gray-500"
              />
            </div>
          </div>

          <div>
            <Label>Role</Label>
            <div className="relative">
              <Shield className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={formatRole(user.role)}
                disabled
                className="w-full rounded-lg border border-gray-100 bg-gray-50 py-2 pl-10 pr-3 text-sm text-gray-500"
              />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#ea580c] disabled:opacity-50"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              Save Changes
            </button>
          </div>
        </div>
      </div>

      {/* Password Change */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-900">
          <Lock className="h-4 w-4 text-gray-400" />
          Change Password
        </h3>
        <div className="space-y-4">
          <div>
            <Label required>Current Password</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter current password"
                className="w-full rounded-lg border border-gray-200 py-2 pl-10 pr-3 text-sm text-gray-900 transition-colors focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label required>New Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="New password"
                  className="w-full rounded-lg border border-gray-200 py-2 pl-10 pr-3 text-sm text-gray-900 transition-colors focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
                />
              </div>
            </div>
            <div>
              <Label required>Confirm Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  className="w-full rounded-lg border border-gray-200 py-2 pl-10 pr-3 text-sm text-gray-900 transition-colors focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
                />
              </div>
            </div>
          </div>

          {newPassword && confirmPassword && newPassword !== confirmPassword && (
            <p className="text-xs text-red-500">Passwords do not match</p>
          )}

          <div className="flex justify-end pt-2">
            <button
              onClick={handlePasswordChange}
              disabled={changingPassword || !currentPassword || !newPassword || !confirmPassword || newPassword !== confirmPassword}
              className="inline-flex items-center gap-2 rounded-lg bg-gray-900 px-5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-gray-800 disabled:opacity-50"
            >
              {changingPassword && <Loader2 className="h-4 w-4 animate-spin" />}
              Change Password
            </button>
          </div>
        </div>
      </div>

      {/* Account info */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h3 className="mb-3 text-sm font-semibold text-gray-900">Account</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">User ID</span>
            <span className="font-mono text-gray-700">#{user.id}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
