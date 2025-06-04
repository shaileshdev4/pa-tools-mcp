namespace DarenaHealth.Community.PrValidator.Commands;

public interface ICommandHandler<T>
    where T : ICommand
{
    Task<bool> HandleAsync(T command);
}
