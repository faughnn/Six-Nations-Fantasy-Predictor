import { cn } from '../../utils';

interface BudgetTrackerProps {
  totalCost: number;
  remainingBudget: number;
}

export function BudgetTracker({ totalCost, remainingBudget }: BudgetTrackerProps) {
  const isOverBudget = remainingBudget < 0;
  const budgetPercent = Math.min((totalCost / 230) * 100, 100);

  return (
    <div className="card">
      <h3 className="font-semibold mb-3">Budget</h3>

      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span>Used: {totalCost.toFixed(1)}</span>
          <span>Total: 230</span>
        </div>
        <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full transition-all',
              isOverBudget ? 'bg-red-500' : 'bg-primary-500'
            )}
            style={{ width: `${budgetPercent}%` }}
          />
        </div>
      </div>

      <div
        className={cn(
          'text-2xl font-bold text-center p-3 rounded-lg',
          isOverBudget ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'
        )}
        data-testid="budget-remaining"
      >
        {remainingBudget.toFixed(1)} remaining
      </div>

      {isOverBudget && (
        <p className="text-red-600 text-sm mt-2 text-center">
          Over budget! Remove players to continue.
        </p>
      )}
    </div>
  );
}
